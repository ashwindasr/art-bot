from artbotlib import exceptions, constants
from artbotlib import pipeline_image_util
import requests

API = "http://art-dash-server-art-build-dev.apps.ocp4.prod.psi.redhat.com/api/v1"


def image_pipeline(so, starting_from, repo_name, version):
    so.say("Fetching data. Please wait...")

    if not version:
        version = "4.10"  # Default version set to 4.10, if unspecified

    url = f"{API}/pipeline-image"
    params = {
        "starting_from": f"{starting_from}",
        "name": f"{repo_name}",
        "version": f"{version}"
    }

    response = requests.get(url, params=params)
    result = response.json().get("payload")

    try:
        if response.status_code == 200:
            slack_output = ""

            slack_output += f"Upstream GitHub repository: <{result['upstream_github_url']}|*openshift/{result['github_repo']}*>\n"
            slack_output += f"Private GitHub repository: <{result['private_github_url']}|*openshift-priv/{result['github_repo']}*>\n"

            distgits = result['distgit']
            if len(distgits) > 1:
                slack_output += f"\n*More than one dist-gits were found for the GitHub repo `{result['github_repo']}`*\n\n"

            for distgit in distgits:
                slack_output += f"Production dist-git repo: <{distgit['distgit_url']}|*{distgit['distgit_repo_name']}*>\n"

                slack_output += f"Production brew builds: <{distgit['brew']['brew_build_url']}|*{distgit['brew']['brew_package_name']}*>\n"

                if distgit['brew']['payload_tag'] != "None":
                    slack_output += f"Payload tag: *{distgit['brew']['payload_tag']}* \n"
                if distgit['brew']['bundle_component'] != "None":
                    slack_output += f"Bundle Component: *{distgit['brew']['bundle_component']}* \n"
                if distgit['brew']['bundle_distgit'] != "None":
                    slack_output += f"Bundle Distgit: *{distgit['brew']['bundle_distgit']}* \n"

                cdn_repos = distgit['brew']['cdn']

                if len(cdn_repos) > 1:
                    slack_output += "\n *Found more than one Brew to CDN mappings:*\n\n"

                for cdn_repo in cdn_repos:
                    slack_output += f"CDN repo: <{cdn_repo['cdn_repo_url']}|*{cdn_repo['cdn_repo_name']}*>\n"
                    slack_output += f"Delivery (Comet) repo: <{cdn_repo['delivery']['delivery_repo_url']}|*{cdn_repo['delivery']['delivery_repo_name']}*>\n\n"
            so.say(slack_output)
        else:
            so.say(f"{result}")
            so.monitoring_say(f"{result}")
    except Exception as e:
        so.say(f"Error. Contact ART Team")
        so.monitoring_say(f"Error: {e} \nPayload: {result}")
