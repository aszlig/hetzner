{ nixpkgs ? <nixpkgs>
, systems ? [ "armv6l-linux" "armv7l-linux" "i686-linux" "x86_64-linux" ]
}:

let
  inherit (import nixpkgs {}) lib;

  getPythonName = name: let
    match = builtins.match "python([0-9]{2,})Packages" name;
    cpython = if match != null then "python${lib.head match}" else null;
  in if name == "pypyPackages" then "pypy" else cpython;

  getPythonSetsFor = system: let
    pkgs = import nixpkgs { inherit system; };
    getPythonSet = name: acc: let
      pyname = getPythonName name;
      newAcc = acc // { ${pyname} = pkgs.${name}; };
    in if pyname == null then acc else newAcc;
  in lib.fold getPythonSet {} (lib.attrNames pkgs);

  mkPackageSet = system: pyver: pythonPackages: let
    pkgs = import nixpkgs { inherit system; };
  in { hetzner = import ./. { inherit pythonPackages; }; };

  mkSystems = system: let
    pythonSets = getPythonSetsFor system;
  in lib.mapAttrs (mkPackageSet system) pythonSets;

in lib.genAttrs systems mkSystems
