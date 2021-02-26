import json

def write(obj, id):
    with open(str(id) + ".json", "w") as outfile:
        fileVar = json.dumps(obj, indent=4)
        outfile.write(fileVar)


def read(id):
    with open(str(id) + ".json", "r") as openfile:
        info = json.load(openfile)
        return info