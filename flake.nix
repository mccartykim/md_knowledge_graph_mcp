{
  description = "Knowledge Graph MCP Server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    uv2nix,
    pyproject-nix,
    ...
  }:
  let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
    python = pkgs.python312; # Or another suitable Python version
    # Load a uv workspace from a workspace root.
    # Uv2nix treats all uv projects as workspace projects.
    workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
    mkVenv = pyproject-nix.build.packages {
      inherit python;
    };
    # Create package overlay from workspace.
    overlay = workspace.mkPyprojectOverlay {};
    pythonSet = mkVenv.overrideScope
    (
      lib.composeManyExtensions [
        overlay
      ]
    );
  in
  {
    # Build the server into a virtual environment.
    packages.x86_64-linux.default = pythonSet.mkVirtualEnv "knowledge-graph-server-env" workspace.deps.default;

    # Run the server with `nix run`.
    apps.x86_64-linux = {
      default = {
        type = "app";
        program = "${self.packages.x86_64-linux.default}/bin/uvx"; # Assuming that uvx is in the venv
        args = [
          "run"
          "server.py"
        ];
      };
    };

    devShells.x86_64-linux.default = pkgs.mkShell {
      packages = [
        python
        pkgs.uv
      ];
      shellHook = ''
        echo "Entering development shell for knowledge graph server."
        echo "To run the server: nix run"
        echo "To enter a shell: nix develop"
        unset PYTHONPATH
      '';

      # prevent uv from managing python downloads
      UV_PYTHON_DOWNLOADS = "never";
    };
  };
}