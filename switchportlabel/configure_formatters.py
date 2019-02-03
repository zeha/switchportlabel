def format_cisco_nxos(ports):
    linesets = []
    for switchport, detail in ports.items():
        port_lines = []

        command = "switchport description" if detail["type"] == "Fibre Channel" else "description"
        new_description = detail.get("new_description", None)
        old_description = detail.get("description", None)
        if new_description and new_description != old_description:
            if old_description:
                port_lines.append("#   before: %s" % (old_description,))
            port_lines.append("  %s %s" % (command, new_description))
        # elif detail.get('description', None):
        #     port_lines.append("-- was %s" % detail['description'])
        #     port_lines.append("  no %s" % command)

        if port_lines:
            linesets.append(["interface %s" % switchport] + port_lines + ["exit"])
    return linesets


def format_hp_comware(ports):
    linesets = []
    for switchport, detail in ports.items():
        port_lines = []

        command = "description"
        new_description = detail.get("new_description", None)
        old_description = detail.get("description", None)
        if new_description and new_description != old_description:
            if old_description:
                port_lines.append("  # before: %s" % (old_description,))
            port_lines.append("  %s %s" % (command, new_description))
        # elif detail.get('description', None):
        #     port_lines.append("-- was %s" % detail['description'])
        #     port_lines.append("  no %s" % command)

        if port_lines:
            linesets.append(["interface %s" % switchport] + port_lines + ["quit"])
    return linesets


def format_for(switch):
    device_type = switch["device_type"]
    if device_type == 'none':
        return None
    elif device_type == "cisco_nxos":
        return format_cisco_nxos(switch["interfaces"])
    elif device_type == "hp_comware":
        return format_hp_comware(switch["interfaces"])
    else:
        raise KeyError(device_type)
