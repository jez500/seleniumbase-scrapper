# Process cleanup and the zombie-process fix

## The symptom

A long-running container accumulated zombie processes. Every scrape added
about 12 of them. Production reached 9,418 zombies. The API then failed with:

```
RuntimeError: can't start new thread
```

The main process stayed alive, so Kubernetes never restarted the pod.
The `/health` endpoint kept returning HTTP 200, because it does not start a
browser.

## Two separate causes

The leak had two independent causes. They need two independent fixes.

### Cause 1: PID 1 did not reap orphaned descendants

`api/docker-entrypoint-api.sh` ran `exec python3 /SeleniumBase/api/server.py`.
Python therefore became PID 1.

Chrome starts many descendant processes. Examples are renderer processes,
`chrome_crashpad_handler` and the `cat` processes that `xdg-settings` starts.
Those processes are grandchildren of the Python process, not children of it.
When their own parent exits, the kernel reparents them to PID 1.

PID 1 must call `wait()` on reparented children. Python never does this, so
each reparented child stayed in the process table as a zombie forever. This
accounted for 11 of the 12 zombies per scrape.

**Fix:** the image now runs Tini as PID 1. Tini reaps every orphan it inherits
and forwards signals to the entrypoint script. See the `ENTRYPOINT` line in the
`Dockerfile`. The image no longer depends on `docker run --init` or on the
Compose `init: true` setting, so Kubernetes gets the same behaviour.

### Cause 2: SeleniumBase abandons one chromedriver child per driver

The remaining zombie was a `uc_driver` process parented to the Python process
itself. Tini cannot help here, because Python is the real parent. A parent must
reap its own children.

The chain is:

1. `seleniumbase/core/browser_launcher.py` calls `driver.connect()` after the
   UC-mode driver is already running.
2. `seleniumbase/undetected/__init__.py` `connect()` calls
   `self.service.start()` on the same `Service` object.
3. Selenium's `Service.start()` assigns a **new** `subprocess.Popen` to
   `Service.process` and overwrites the old one.
4. The old chromedriver process exits, but nobody ever calls `wait()` on the
   replaced `Popen` object. The process stays a zombie.

Verified on SeleniumBase 4.44.10 with Selenium 4.38.0.

This leak is **bounded, not cumulative**. CPython records a dropped-but-unwaited
`Popen` in `subprocess._active`. The next `subprocess.Popen(...)` call runs
`subprocess._cleanup()`, which polls those objects and reaps them. The next
scrape therefore reaps the previous scrape's zombie. A controlled test showed a
steady count of one, with a different PID after every scrape.

**Fix:** `helpers.reap_abandoned_child_processes()` polls the entries in
`subprocess._active` and then prunes the list. `api/endpoints/article.py` calls
it in the `finally` block of every scrape.

The helper only touches `Popen` objects that this process created and then
dropped. It never calls `waitpid(-1)`, and it never kills a process by name.
Both of those would race with Selenium, SeleniumBase or any other library that
still waits for a child of its own.

The `finally` block also wraps `driver.quit()` in its own `try`. A failed
`quit()` must not skip the reap.

## Measured results

Both runs used `scripts/test-container-zombies`, 10 scrapes of a local HTML
data URL, on `linux/amd64`. Neither run reached an external website.

| Scrape | Before the fix | Tini alone | After the full fix |
|--------|---------------:|-----------:|-------------------:|
| 1      | 23             | 0          | 0 |
| 2      | 36             | 1          | 0 |
| 3      | 48             | 1          | 0 |
| 4      | 60             | 1          | 0 |
| 5      | 72             | 1          | 0 |
| 10     | 132            | 1          | 0 |

The "Tini alone" column comes from the unchanged `v1.0` image started with
`docker run --init`.

A longer soak of the fixed image ran 25 scrapes, then three unreachable-URL
scrapes, one forced `Driver()` failure and one recovery scrape. The zombie
count stayed at 0 for all 30 requests. The total process count inside the
container stayed at 3.

Growth before the fix was linear at 12 zombies per scrape. At that rate the
observed production figure of 9,418 zombies corresponds to roughly 785 scrapes.

The fixed image also stops faster. `docker stop` on the old image needed the
full 30-second timeout and exited with code 137 (SIGKILL). The fixed image
exits in under one second with code 143 (SIGTERM).

## Known limitations

- The arm64 image was not tested here. This machine has no qemu binfmt setup,
  so only `linux/amd64` was built and measured. The `tini` package exists for
  arm64 in Ubuntu 22.04, and the reaper is architecture-independent.
- `reap_abandoned_child_processes()` reads `subprocess._active`, which is a
  CPython implementation detail. The helper returns 0 when the attribute is
  missing, so a future Python release can only make the helper inert. It cannot
  make it raise. A unit test covers that case.
- The helper reaps children that have already exited. It does not kill a child
  that is still running. If a `Driver()` call fails and leaves a live Chrome
  process behind, Tini reaps that process only after it exits on its own.
- The fix does not change `/health`. That endpoint still returns a static HTTP
  200 and does not prove that a browser can start.

## Running the regression test

```bash
# Build the image first
docker build -t seleniumbase-scrapper:test .

# Run the test. The second argument is the number of scrapes.
./scripts/test-container-zombies seleniumbase-scrapper:test 10
```

The script:

1. Starts a container **without** `--init`, so the image must reap orphans
   itself.
2. Checks that PID 1 runs Tini.
3. Scrapes a local HTML data URL the requested number of times. It counts
   processes and zombies inside the container after every scrape, and prints the
   PID, parent PID and command of each zombie.
4. Scrapes a URL that no server answers.
5. Hides the Chrome binary to force a `Driver()` failure, then checks that the
   API recovers.
6. Stops the container and checks that it exits before the kill timeout.
7. Removes the container on every exit path, including an interrupt.

Every step uses a bounded timeout. The script exits 0 only when all checks pass.

Running it against the old image reproduces the leak and fails:

```bash
./scripts/test-container-zombies jez500/seleniumbase-scrapper:v1.0 10
```
