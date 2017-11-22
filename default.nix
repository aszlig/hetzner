{ pythonPackages ? (import <nixpkgs> {}).pythonPackages }:

pythonPackages.buildPythonPackage rec {
  name = "hetzner-${version}";
  version = let
    matchVersion = builtins.match ".*version=[\"']([^\"']+)[\"'].*";
  in builtins.head (matchVersion (builtins.readFile ./setup.py));
  src = ./.;
}
