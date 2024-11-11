# Base image: Ruby with necessary dependencies for Jekyll
FROM ccr-23gxup9u-vpc.cnc.bj.baidubce.com/common/ruby:3.2

COPY apt_source.txt /etc/apt/sources.list

RUN gpg --keyserver keyserver.ubuntu.com --recv 871920D1991BC93C && gpg --export --armor 871920D1991BC93C | apt-key add -

# Install dependencies
RUN rm /etc/apt/sources.list.d/debian.sources && apt-get update && apt-get install -y \
    build-essential \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy Gemfile into the container (necessary for `bundle install`)
COPY Gemfile ./

# Install bundler and dependencies
RUN gem install bundler:2.3.26 && bundle install

# Expose port 4000 for Jekyll server
EXPOSE 4000

# Command to serve the Jekyll site
CMD ["bundle", "exec", "jekyll", "serve", "--host", "localhost", "--watch"]

