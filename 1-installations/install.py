# IMPORTS
import sys
import subprocess
import importlib.util



# FUNCTIONS
def install_package(package_name, import_name=None):
    if import_name is None:
        import_name = package_name

    if importlib.util.find_spec(import_name) is None:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"{package_name} installed successfully!")
    else:
        print(f"{package_name} is already installed.")


def main():
    packages = {
        "clingo": "clingo",
        "matplotlib": "matplotlib"
    }

    for package_name, import_name in packages.items():
        install_package(package_name, import_name)

    print("All required packages are installed.")



if __name__ == "__main__":
    main()
