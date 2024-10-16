Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
  config.vm.hostname = "chep"
  config.disksize.size = '100GB'

  config.vm.provider "virtualbox" do |v|
      v.memory = 4000
      v.cpus = 2
  end
end
