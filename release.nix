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

  mkPackageSet = system: pyver: let
    pkgs = import nixpkgs { inherit system; };
    pythonPackages = pkgs."${pyver}Packages";
  in {
    hetzner = import ./. { inherit pythonPackages; };
  };

  mkSystems = system: lib.genAttrs pythonVersions (mkPackageSet system);

in lib.genAttrs systems mkSystems
