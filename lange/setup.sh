#/bin/bash

# cvmfs
sudo apt install lsb-release -y
if [ ! -f /tmp/cvmfs-release-latest_all.deb ]; then
        wget https://ecsft.cern.ch/dist/cvmfs/cvmfs-release/cvmfs-release-latest_all.deb -O /tmp/cvmfs-release-latest_all.deb
fi
sudo dpkg -i /tmp/cvmfs-release-latest_all.deb
sudo apt update
sudo apt install -y cvmfs
sudo cvmfs_config setup
sudo sh -c "echo "CVMFS_HTTP_PROXY=DIRECT" > /etc/cvmfs/default.local"
sudo sh -c "echo "CVMFS_DEBUGLOG=/tmp/cvmfs.log" >> /etc/cvmfs/default.local"
sudo cvmfs_config reload

# go
if [ ! -f /tmp/go1.22.0.linux-amd64.tar.gz ]; then
        sudo wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz -P /tmp
fi
sudo tar -C /usr/local -xvf /tmp/go1.22.0.linux-amd64.tar.gz

echo "export GOPATH=$HOME/go" >> ~/.bashrc
echo "export PATH=\$PATH:/usr/local/go/bin:\$GOPATH/bin" >> ~/.bashrc
source ~/.bashrc

# cvmfs-snapshotter
if [ ! -d /tmp/cvmfs ]; then
        git clone https://github.com/cvmfs/cvmfs /tmp/cvmfs
fi
cd /tmp/cvmfs/snapshotter 
/usr/local/go/bin/go build -o out/cvmfs_snapshotter -ldflags '-X main.Version=2.11'                                                                        
cp /tmp/cvmfs/snapshotter/out/cvmfs_snapshotter /usr/local/bin/cvmfs_snapshotter
wget https://raw.githubusercontent.com/cvmfs/cvmfs/42e04529dc8eccb52bf62b27b220aa54b660681a/snapshotter/script/config/etc/systemd/system/cvmfs-snapshotter.service -O /etc/systemd/system/cvmfs-snapshotter.service
mkdir -p /etc/containerd-cvmfs-grpc && touch /etc/containerd-cvmfs-grpc/config.toml

sudo systemctl daemon-reload
sudo systemctl start cvmfs-snapshotter

# k3s 
if [[ -f "/usr/local/bin/k3s-uninstall.sh" ]]; then
    sudo /usr/local/bin/k3s-uninstall.sh
fi
curl -sfL https://get.k3s.io | sh -
sudo tee /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl > /dev/null <<EOF
version = 2
[plugins."io.containerd.grpc.v1.cri".containerd]
  snapshotter = "cvmfs-snapshotter"
  disable_snapshot_annotations = false
[proxy_plugins]
  [proxy_plugins.cvmfs-snapshotter]
    type = "snapshot"
    address = "/run/containerd-cvmfs-grpc/containerd-cvmfs-grpc.sock"
[plugins."io.containerd.grpc.v1.cri".cni]
  bin_dir = "/var/lib/rancher/k3s/data/current/bin"
  conf_dir = "/var/lib/rancher/k3s/agent/etc/cni/net.d"
EOF
systemctl restart k3s

if [ ! -f /tmp/0431F9FA-6202-E311-8B98-002481E1501E.root ]; then
	wget http://opendata.cern.ch/record/9538/files/assets/cms/MonteCarlo2012/Summer12_DR53X/TTGJets_8TeV-madgraph/AODSIM/PU_RD1_START53_V7N-v1/10000/0431F9FA-6202-E311-8B98-002481E1501E.root -P /tmp
fi

echo "alias k=kubectl" >> ~/.bashrc
