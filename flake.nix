{
  description = "A Nix-flake-based nlogo development environment";

  inputs = {
    nixpkgs.url = "github:hatch01/nixpkgs/netlogo";
    flake-parts.url = "github:hercules-ci/flake-parts";
    systems.url = "github:nix-systems/default";
  };

  outputs =
    inputs@{ self, flake-parts, ... }:

    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = import inputs.systems;

      perSystem =
        { pkgs, ... }:
        {
          devShells.default = pkgs.mkShell {
            packages = with pkgs; [
              netlogo
              python314Packages.pandas
              python314Packages.matplotlib
              python314
            ];
          };
        };
    };
}
