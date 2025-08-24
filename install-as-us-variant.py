#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime

VARIANTS_TO_INSTALL = {
    "carbon": "English (Carbon)",
    "carbon-angle": "English (Carbon, Angle Mod)"
}

SYMBOL_FILE_NAME = "carbon-as-variant"
TARGET_SYMBOL_FILE_NAME = "us"  # append into us

BASE_LAYOUT = "us"

XKB_SYMBOLS_DIR = "/usr/share/X11/xkb/symbols"
XKB_RULES_FILES = [
    "/usr/share/X11/xkb/rules/evdev.xml",
    "/usr/share/X11/xkb/rules/base.xml"
]


def check_root_privileges():
    if os.geteuid() != 0:
        print("Error: This script must be run with root privileges.")
        sys.exit(1)


def backup_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.bak_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"  -> Created backup: {backup_path}")


def modify_xkb_rules(action):
    for xml_file in XKB_RULES_FILES:
        if not os.path.exists(xml_file):
            print(f"Warning: Rules file not found, skipping: {xml_file}")
            continue

        print(f"\nProcessing: {xml_file}")
        backup_file(xml_file)

        try:
            ET.register_namespace('', 'http://www.freedesktop.org/xkeyboard-config')
            tree = ET.parse(xml_file)
            root = tree.getroot()

            layout_node = None
            for layout in root.findall(".//layout"):
                name_el = layout.find("./configItem/name")
                if name_el is not None and name_el.text == BASE_LAYOUT:
                    layout_node = layout
                    break

            if layout_node is None:
                print(f"Error: Base layout '{BASE_LAYOUT}' not found in {xml_file}.")
                continue

            variant_list = layout_node.find('variantList')
            if variant_list is None and action == 'install':
                variant_list = ET.SubElement(layout_node, 'variantList')

            for name, description in VARIANTS_TO_INSTALL.items():
                existing_variants = []
                if variant_list is not None:
                    for variant in variant_list.findall('variant'):
                        variant_name_el = variant.find('./configItem/name')
                        if variant_name_el is not None and variant_name_el.text == name:
                            existing_variants.append(variant)

                if action == 'remove':
                    for variant in existing_variants:
                        variant_list.remove(variant)
                        print(f"  - Removed variant '{name}'.")

                elif action == 'install':
                    for variant in existing_variants:
                        variant_list.remove(variant)

                    new_variant = ET.Element('variant')
                    config_item = ET.SubElement(new_variant, 'configItem')
                    name_tag = ET.SubElement(config_item, 'name')
                    name_tag.text = name
                    desc_tag = ET.SubElement(config_item, 'description')
                    desc_tag.text = description
                    variant_list.append(new_variant)
                    print(f"  + Added variant '{name}'.")

            ET.indent(tree, space='  ')
            tree.write(xml_file, encoding='UTF-8', xml_declaration=True)

        except ET.ParseError as e:
            print(f"Error parsing XML file {xml_file}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)


def install():
    print("--- Starting Carbon Layout Installation ---")

    source_file = os.path.join(os.path.dirname(__file__), SYMBOL_FILE_NAME)
    if not os.path.exists(source_file):
        print(f"Error: Symbol file '{source_file}' not found.")
        sys.exit(1)

    destination_file = os.path.join(XKB_SYMBOLS_DIR, TARGET_SYMBOL_FILE_NAME)
    backup_file(destination_file)

    print(f"\nAppending '{source_file}' into '{destination_file}'...")
    try:
        with open(source_file, "r") as src, open(destination_file, "a") as dst:
            dst.write("\n\n")
            dst.write(src.read())
        print("Symbol variants appended successfully.")
    except IOError as e:
        print(f"Error: Could not append to symbols file. {e}")
        sys.exit(1)

    modify_xkb_rules('install')

    print("\n--- Installation Complete ---")
    print("To apply changes, please log out and log back in.")


def remove():
    print("--- Starting Carbon Layout Uninstallation ---")

    target_file = os.path.join(XKB_SYMBOLS_DIR, TARGET_SYMBOL_FILE_NAME)
    if os.path.exists(target_file):
        backup_file(target_file)
        print(f"\nCleaning Carbon variants from: {target_file}...")
        try:
            with open(target_file, "r") as f:
                lines = f.readlines()

            new_lines = []
            skip = False
            for line in lines:
                if line.strip().startswith('xkb_symbols "carbon"') or \
                   line.strip().startswith('xkb_symbols "carbon-angle"'):
                    skip = True
                if skip and line.strip().startswith('};'):
                    skip = False
                    continue
                if not skip:
                    new_lines.append(line)

            with open(target_file, "w") as f:
                f.writelines(new_lines)

            print("Removed Carbon variants from symbols file.")
        except OSError as e:
            print(f"Error: Could not clean symbols file. {e}")
            sys.exit(1)

    modify_xkb_rules('remove')

    print("\n--- Uninstallation Complete ---")
    print("To apply changes, please log out and log back in.")


def main():
    check_root_privileges()

    parser = argparse.ArgumentParser(
        description="Install or remove the Carbon XKB layout variants.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--install', action='store_true', help="Install the Carbon layout variants.")
    group.add_argument('-r', '--remove', action='store_true', help="Remove (uninstall) the Carbon layout variants.")

    args = parser.parse_args()

    if args.install:
        install()
    elif args.remove:
        remove()


if __name__ == "__main__":
    main()

