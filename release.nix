{ nixpkgs ? <nixpkgs>
, systems ? [
    "armv6l-linux" "armv7l-linux" "i686-linux" "x86_64-linux"
  ]
, pythonVersions ? [
    "python27" "python33" "python34" "python35" "python36" "pypy"
  ]
}:

let
  inherit (import nixpkgs {}) lib;

  mkPackageSet = pyver: system: let
    pkgs = import nixpkgs { inherit system; };
    pythonPackages = pkgs."${pyver}Packages";
  in {
    hetzner = import ./. { inherit pythonPackages; };
  };

  mkSystems = pyver: lib.genAttrs systems (mkPackageSet pyver);

in lib.genAttrs pythonVersions mkSystems
