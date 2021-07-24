{
  description = "High level access to the Hetzner robot";

  outputs = { self, nixpkgs }: let
    inherit (nixpkgs) lib;

    hydraSystems = [ "i686-linux" "x86_64-linux" ];

    mkPackage = pythonPackages: pythonPackages.buildPythonPackage {
      pname = "hetzner";

      version = let
        matchVersion = builtins.match ".*version=[\"']([^\"']+)[\"'].*";
      in builtins.head (matchVersion (builtins.readFile ./setup.py));

      src = self;
    };

  in {
    packages = lib.mapAttrs (lib.const (pkgs: {
      hetzner = mkPackage pkgs.python3Packages;
    })) nixpkgs.legacyPackages;

    defaultPackage = let
      getPackage = system: lib.const (self.packages.${system}.hetzner);
    in lib.mapAttrs getPackage nixpkgs.legacyPackages;

    checks = lib.mapAttrs (system: pkgs: let
      interpreters = removeAttrs pkgs.pythonInterpreters [
        # These fail to eveluate or build (the latter because we require TLS).
        "graalpython37" "python3Minimal"
      ];
      isEligible = lib.const (interpreter: let
        rightPlatform = lib.elem system interpreter.meta.platforms;
        rightVersion = interpreter.pythonAtLeast "3.7";
      in interpreter ? pythonAtLeast && rightVersion && rightPlatform);
      supported = lib.filterAttrs isEligible interpreters;
      mkInterpreterPackage = lib.const (interpreter: {
        name = lib.removeSuffix "3" interpreter.pname
             + "-${interpreter.pythonVersion}";
        value = mkPackage interpreter.pkgs;
      });
    in lib.mapAttrs' mkInterpreterPackage supported) nixpkgs.legacyPackages;

    hydraJobs = lib.genAttrs hydraSystems (system: let
      # Hydra doesn't allow job names containing periods.
      mangleName = lib.replaceStrings [ "." ] [ "_" ];
      mangleAttrName = name: lib.nameValuePair (mangleName name);
    in lib.mapAttrs' mangleAttrName self.checks.${system});
  };
}
