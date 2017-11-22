{ pythonPackages ? (import <nixpkgs> {}).pythonPackages }:

pythonPackages.buildPythonPackage rec {
  name = "hetzner-${version}";
  version = let
    matchVersion = builtins.match ".*version=[\"']([^\"']+)[\"'].*";
  in builtins.head (matchVersion (builtins.readFile ./setup.py));

  src = let
    filter = path: type: let
      name = baseNameOf (toString path);
      dirCond = name == ".git" || name == "build" || name == "dist";
      linkCond = builtins.match "result.*" name != null;
      cond = builtins.match ".*\\.py[oc]$" name != null
          || builtins.match ".*\\.sw[a-z]$" name != null
          || name == "MANIFEST";
    in if type == "directory" then !dirCond
       else if type == "symlink" then !linkCond
       else !cond;
  in builtins.filterSource filter ./.;
}
