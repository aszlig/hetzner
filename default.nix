with import <nixpkgs> {};

pythonPackages.buildPythonPackage rec {
  name = "hetzner-${version}";
  version = "0.7.1";
  src = ./.;
}
