# Only needed during first-time setup:
wget http://packages.couchbase.com/releases/couchbase-release/couchbase-release-1.0-2-amd64.deb
sudo dpkg -i couchbase-release-1.0-2-amd64.deb
sudo apt-get update
sudo apt-get install libcouchbase-dev build-essential python-dev python-pip
sudo pip install couchbase
