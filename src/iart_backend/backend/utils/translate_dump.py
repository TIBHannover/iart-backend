import json

import os
import sys
import re
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('-i', '--input',  help='verbose output')
    parser.add_argument('-o', '--output',  help='verbose output')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    
    data= []
    with open(args.input, 'r') as f:
        data=json.load(f)

    new_data = []
    for line in data:
        print('########')
        print(line)
        if 'model' not in line:
            new_data.append(line)
            continue
        # print(line)
        line["model"] = re.sub('frontend.', 'backend.', line["model"])

        if line["model"] == "contenttypes.contenttype":
            line["fields"]["app_label"]="backend"
        # print(line)
        print(line)
        new_data.append(line)

    with open(args.output, 'w') as f:
        json.dump(new_data, f)

    # print(json.dumps(new_data))
        # input()
    return 0

if __name__ == '__main__':
    sys.exit(main())