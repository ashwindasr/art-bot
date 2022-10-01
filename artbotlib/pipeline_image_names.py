import json

from artbotlib import exceptions
from artbotlib import pipeline_image_util
import requests

API = "http://localhost:8080/api/v1"


# Driver functions
def image_pipeline(so, type, repo_name, version):
    try:
        so.say("Fetching data. Please wait...")

        if not version:
            version = "4.10"  # Default version set to 4.10, if unspecified

        url = f"{API}/pipeline-image"
        params = {
            "starting_from": f"{type}",
            "name": f"{repo_name}",
            "version": f"{version}"
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            slack_output = ""
            result = json.loads(response.json()).get("payload")

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
                    slack_output += f"Delivery (Comet) repo: <{cdn_repo['delivery']['delivery_repo_url']}|*{cdn_repo['delivery']['delivery_repo']}*>\n\n"
            so.say(slack_output)
        else:
            raise Exception("API Server Error")
    except Exception as e:
        so.say("Error. Contact ART team")
        so.monitoring_say(f"Error. {e}")


def pipeline_from_distgit(so, distgit_repo_name, version):
    """
    Function to list the GitHub repo, Brew package name, CDN repo name and delivery repo by getting the distgit name as input.

    GitHub <- Distgit -> Brew -> CDN -> Delivery

    :so: SlackOutput object for reporting results.
    :distgit_repo_name: Name of the distgit repo we get as input
    :version: OCP version
    """
    if not version:
        version = "4.10"  # Default version set to 4.10, if unspecified
    variant = f"8Base-RHOSE-{version}"

    payload = ""

    if not pipeline_image_util.distgit_is_available(
            distgit_repo_name):  # Check if the given distgit repo actually exists
        # If incorrect distgit name provided, no need to proceed.
        payload += f"No distgit repo with name *{distgit_repo_name}* exists. Try again\n"
        payload += "Example format: *what is the image pipeline for distgit `ironic`*"

        so.say(payload)
        return
    else:
        so.say("Fetching data. Please wait...")
        try:
            # Distgit -> GitHub
            github_repo = pipeline_image_util.distgit_to_github(distgit_repo_name, version)
            payload += f"Upstream GitHub repository: <https://github.com/openshift/{github_repo}|*openshift/{github_repo}*>\n"
            payload += f"Private GitHub repository: <https://github.com/openshift-priv/{github_repo}|*openshift-priv/{github_repo}*>\n"

            # Distgit
            payload += f"Production dist-git repo: <https://pkgs.devel.redhat.com/cgit/containers/{distgit_repo_name}|*{distgit_repo_name}*>\n"

            # Distgit -> Delivery
            payload += pipeline_image_util.distgit_to_delivery(distgit_repo_name, version, variant)
        except exceptions.ArtBotExceptions as e:
            payload += "\n"
            payload += f"{e}"
            so.say(payload)
            so.monitoring_say(f"ERROR: {e}")
            return
        except exceptions.InternalServicesExceptions as e:
            so.say(f"{e}. Contact the ART Team")
            so.monitoring_say(f"ERROR: {e}")
            return
        except Exception as e:
            so.say("Unknown error. Contact the ART team.")
            so.monitoring_say(f"ERROR: Unclassified: {e}")
    so.say(payload)


def pipeline_from_brew(so, brew_name, version):
    """
    Function to list the GitHub repo, Brew package name, CDN repo name and delivery repo by getting the brew name as input.

    GitHub <- Distgit <- Brew -> CDN -> Delivery

    :so: SlackOutput object for reporting results.
    :brew_name: Name of the brew repo we get as input
    :version: OCP version
    """
    if not version:
        version = "4.10"  # Default version set to 4.10, if unspecified
    variant = f"8Base-RHOSE-{version}"

    payload = ""

    if not pipeline_image_util.brew_is_available(brew_name):  # Check if the given brew repo actually exists
        # If incorrect brew name provided, no need to proceed.
        payload += f"No brew package with name *{brew_name}* exists. Try again\n"
        payload += "Example format: *what is the image pipeline for package `ironic-container`*"

        so.say(payload)
        return
    else:
        so.say("Fetching data. Please wait...")
        try:
            # Brew -> GitHub
            payload += pipeline_image_util.brew_to_github(brew_name, version)

            # Brew
            brew_id = pipeline_image_util.get_brew_id(brew_name)
            payload += f"Production brew builds: <https://brewweb.engineering.redhat.com/brew/packageinfo?packageID={brew_id}|*{brew_name}*>\n"

            # Brew -> Delivery
            payload += pipeline_image_util.brew_to_delivery(brew_name, variant)

        except exceptions.ArtBotExceptions as e:
            payload += "\n"
            payload += f"{e}"
            so.say(payload)
            so.monitoring_say(f"ERROR: {e}")
            return
        except exceptions.InternalServicesExceptions as e:
            so.say(f"{e}. Contact the ART Team")
            so.monitoring_say(f"ERROR: {e}")
            return
        except Exception as e:
            so.say("Unknown error. Contact the ART team.")
            so.monitoring_say(f"ERROR: Unclassified: {e}")
    so.say(payload)


def pipeline_from_cdn(so, cdn_repo_name, version):
    """
    Function to list the GitHub repo, Brew package name, CDN repo name and delivery repo by getting the CDN name as input.

    GitHub <- Distgit <- Brew <- CDN -> Delivery

    :so: SlackOutput object for reporting results.
    :cdn_repo_name: Name of the CDN repo we get as input
    :version: OCP version
    """
    if not version:
        version = "4.10"  # Default version set to 4.10, if unspecified
    variant = f"8Base-RHOSE-{version}"

    payload = ""

    if not pipeline_image_util.cdn_is_available(cdn_repo_name):  # Check if the given brew repo actually exists
        # If incorrect brew name provided, no need to proceed.
        payload += f"No CDN repo with name *{cdn_repo_name}* exists. Try again\n"
        payload += "Example format: *what is the image pipeline for cdn `redhat-openshift4-ose-ironic-rhel8`*"

        so.say(payload)
        return
    else:
        so.say("Fetching data. Please wait...")
        try:
            # CDN -> GitHub
            payload += pipeline_image_util.cdn_to_github(cdn_repo_name, version)

            # CDN
            payload += pipeline_image_util.get_cdn_payload(cdn_repo_name, variant)

            # CDN -> Delivery
            payload += pipeline_image_util.cdn_to_delivery_payload(cdn_repo_name)
        except exceptions.ArtBotExceptions as e:
            payload += "\n"
            payload += f"{e}"
            so.say(payload)
            so.monitoring_say(f"ERROR: {e}")
            return
        except exceptions.InternalServicesExceptions as e:
            so.say(f"{e}. Contact the ART Team")
            so.monitoring_say(f"ERROR: {e}")
            return
        except Exception as e:
            so.say("Unknown error. Contact the ART team.")
            so.monitoring_say(f"ERROR: Unclassified: {e}")
    so.say(payload)


def pipeline_from_delivery(so, delivery_repo_name, version):
    """
    Function to list the GitHub repo, Brew package name, CDN repo name and delivery repo by getting the delivery repo name as input.

    GitHub <- Distgit <- Brew <- CDN <- Delivery

    :so: SlackOutput object for reporting results.
    :delivery_repo_name: Name of the delivery repo we get as input. Example formats:
                                                    registry.redhat.io/openshift4/ose-ironic-rhel8
                                                    openshift4/ose-ironic-rhel8
                                                    ose-ironic-rhel8
    :version: OCP version
    """
    if not version:
        version = "4.10"  # Default version set to 4.10, if unspecified
    variant = f"8Base-RHOSE-{version}"

    payload = ""
    delivery_repo_name = f"openshift4/{delivery_repo_name}"

    if not pipeline_image_util.delivery_repo_is_available(
            delivery_repo_name):  # Check if the given delivery repo actually exists
        # If incorrect delivery repo name provided, no need to proceed.
        payload += f"No delivery repo with name *{delivery_repo_name}* exists. Try again\n"
        payload += "Example format: *what is the image pipeline for image `openshift4/ose-ironic-rhel8`*"

        so.say(payload)
        return
    else:
        so.say("Fetching data. Please wait...")
        try:
            # Brew
            brew_name = pipeline_image_util.brew_from_delivery(delivery_repo_name)
            brew_id = pipeline_image_util.get_brew_id(brew_name)

            # Brew -> GitHub
            payload += pipeline_image_util.brew_to_github(brew_name, version)

            # To make the output consistent
            payload += f"Production brew builds: <https://brewweb.engineering.redhat.com/brew/packageinfo?packageID={brew_id}|*{brew_name}*>\n"

            # Brew -> CDN
            cdn_repo_name = pipeline_image_util.brew_to_cdn_delivery(brew_name, variant, delivery_repo_name)
            payload += pipeline_image_util.get_cdn_payload(cdn_repo_name, variant)

            # Delivery
            delivery_repo_id = pipeline_image_util.get_delivery_repo_id(delivery_repo_name)
            payload += f"Delivery (Comet) repo: <https://comet.engineering.redhat.com/containers/repositories/{delivery_repo_id}|*{delivery_repo_name}*>\n\n"
        except exceptions.ArtBotExceptions as e:
            payload += "\n"
            payload += f"{e}"
            so.say(payload)
            so.monitoring_say(f"ERROR: {e}")
            return
        except exceptions.InternalServicesExceptions as e:
            so.say(f"{e}. Contact the ART Team")
            so.monitoring_say(f"ERROR: {e}")
            return
        except Exception as e:
            so.say("Unknown error. Contact the ART team.")
            so.monitoring_say(f"ERROR: Unclassified: {e}")
    so.say(payload)
