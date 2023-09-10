def generate_ecosystem_args_string(args: list):
    return " ".join([str(a) for a in args])


def generate_ecosystem_app_string(app: dict) -> str:
    if "args" in app and app["args"]:
        return """{{
            name: "{name}",
            script: "{script}",
            args: "{args}"
        }}""".format(name=app["name"], script=app["script"], 
                args=generate_ecosystem_args_string(app["args"]))
    return """{{
            name: "{name}",
            script: "{script}"
        }}""".format(name=app["name"], script=app["script"])

def generate_ecosystem_string(apps: list) -> str:
    return """module.exports = {{
  apps : [{}]
}}
""".format(",".join([generate_ecosystem_app_string(app) for app in apps]))

def generate_ecosystem_file(apps: list) -> None:
    content = generate_ecosystem_string(apps)
    with open("ecosystem.config.js", "w") as f:
        f.write(content)