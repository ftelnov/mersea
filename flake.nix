{
  description = "Mersea — Mermaid diagram visual editor bridge";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux"];
    forAllSystems = f: nixpkgs.lib.genAttrs systems f;
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      mersea = pkgs.python3Packages.buildPythonApplication {
        pname = "mersea";
        version = "0.1.0";
        src = ./.;
        pyproject = true;
        build-system = [pkgs.python3Packages.poetry-core];
        dependencies = with pkgs.python3Packages; [click playwright];
        doCheck = false;
        nativeBuildInputs = [pkgs.makeWrapper];
        postFixup = ''
          wrapProgram $out/bin/mersea \
            --prefix LD_LIBRARY_PATH : "${pkgs.stdenv.cc.cc.lib}/lib"
        '';
      };
    in {
      default = mersea;
      inherit mersea;
    });
  };
}
