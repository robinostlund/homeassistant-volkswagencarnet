"""Update the manifest file."""
import sys
import json
import os


def update_manifest():
    """Update the manifest file."""
    version = "v0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    # read manifest
    with open(f"{os.getcwd()}/custom_components/volkswagencarnet/manifest.json") as manifestfile:
        manifest = json.load(manifestfile)

    # set version in manifest
    manifest["version"] = version

    # read requirements.txt
    with open(f"{os.getcwd()}/requirements.txt") as requirementsfile:
        requirements = [line.rstrip() for line in requirementsfile]

    # set requirements in manifest
    manifest["requirements"] = requirements

    # save manifest
    with open(f"{os.getcwd()}/custom_components/volkswagencarnet/manifest.json", "w") as manifestfile:
        manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))

    # print output
    print("# generated manifest.json")
    for key, value in manifest.items():
        print(f"{key}: {value}")


update_manifest()
