{ pythonPackages ? (import <nixpkgs> {}).pythonPackages }:

pythonPackages.buildPythonPackage rec {
  name = "hetzner-${version}";
  version = "0.7.1";
  src = ./.;
}
