import requests

API = "http://art-dash-server-art-build-dev.apps.ocp4.prod.psi.redhat.com/api/v1"


def translate_names(so, name_type, name, name_type2, major=None, minor=None):
    so.say("Fetching data. Please wait...")
    url = f"{API}/translate-names"
    params = {
        "name_type": f"{name_type}",
        "name": f"{name}",
        "name_type2": f"{name_type2}",
        "major": f"{major}",
        "minor": f"{minor}",

    }

    response = requests.get(url, params=params)
    result = response.json().get("payload")

    try:
        if response.status_code == 200:
            output = result['result']
            major_minor = result['major_minor']

            so.say(f"Image dist-git {name} has {name_type2} '{output}' in version {major_minor}.")

        else:
            so.say(f"{result}")
    except Exception as e:
        so.say(f"Error. Contact ART Team")
        so.monitoring_say(f"Error: {e} \nPayload: {result}")
