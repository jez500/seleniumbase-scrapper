# SeleniumBase Docker Image with API
FROM ubuntu:22.04
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# ARG for SeleniumBase version
ARG SELENIUMBASE_VERSION=v4.44.10

#============================
# Locale Configuration
#============================
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata locales && \
     # Cleanup
     apt-get clean && \
     rm -rf /var/lib/apt/lists/*

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "LANG=en_US.UTF-8" > /etc/locale.conf
RUN locale-gen en_US.UTF-8

#============================
# Install dependencies
#============================
RUN apt-get update && apt-get install -qy --no-install-recommends \
    # Install Linux Dependencies
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libu2f-udev \
    libvulkan1 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    # Install useful utilities
    xdg-utils \
    ca-certificates \
    # Install fonts
    fonts-liberation \
    fonts-liberation2 \
    fonts-font-awesome \
    fonts-ubuntu \
    fonts-terminus \
    fonts-powerline \
    fonts-open-sans \
    fonts-mononoki \
    fonts-roboto \
    fonts-lato \
    # Install Bash Command Line Tools
    curl \
    sudo \
    unzip \
    nano \
    wget \
    xvfb && \
    # Cleanup
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

#============================
# Install Chrome and python.
#============================
RUN apt-get update && \
    # Chrome.
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm ./google-chrome-stable_current_amd64.deb && \
    # Python.
    apt-get install -y python3 python3-pip python3-setuptools python3-dev python3-tk && \
    alias python=python3 && \
    echo "alias python=python3" >> ~/.bashrc && \
    apt-get -qy --no-install-recommends install python3.10 && \
    rm /usr/bin/python3 && \
    ln -s python3.10 /usr/bin/python3 && \
    # Cleanup
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

#============================
# Set up SeleniumBase
#============================
# Download SeleniumBase from GitHub as ZIP
RUN wget https://github.com/seleniumbase/SeleniumBase/archive/refs/tags/${SELENIUMBASE_VERSION}.zip -O /tmp/seleniumbase.zip && \
    unzip /tmp/seleniumbase.zip -d /tmp/ && \
    mv /tmp/SeleniumBase-* /tmp/SeleniumBase && \
    find /tmp/SeleniumBase -name '*.pyc' -delete && \
    pip install --upgrade pip setuptools wheel && \
    cd /tmp/SeleniumBase && pip install -r requirements.txt --upgrade && \
    cd /tmp/SeleniumBase && pip install . && \
    pip install pyautogui flask beautifulsoup4 pytest pytest-mock && \
    # Copy entrypoint scripts from downloaded repo
    cp /tmp/SeleniumBase/integrations/docker/docker-entrypoint.sh / && \
    cp /tmp/SeleniumBase/integrations/docker/run_docker_test_in_chrome.sh / && \
    rm -rf /tmp/SeleniumBase /tmp/seleniumbase.zip

# Copy custom API entrypoint script from local directory
COPY api/docker-entrypoint-api.sh /
RUN chmod +x /*.sh

#============================
# Download chromedriver
#============================
RUN seleniumbase get chromedriver --path

#=======================================
# Copy API files and create directories
#=======================================
COPY api /SeleniumBase/api/
COPY scripts /SeleniumBase/scripts
RUN mkdir -p /SeleniumBase/api/cache
RUN mkdir -p /SeleniumBase/api/screenshots
RUN mkdir -p /SeleniumBase/api/user_scripts
RUN chmod -R 755 /SeleniumBase/api
WORKDIR /SeleniumBase

#============================
# Expose API port
#============================
EXPOSE 8000



ENTRYPOINT ["/docker-entrypoint-api.sh"]
CMD ["/bin/bash"]
