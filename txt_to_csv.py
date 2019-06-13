import csv
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, default=None, help='')


if __name__ == '__main__':
    command_args, _ = parser.parse_known_args()
    filename = command_args.file

    filename = '400water-esquinas-LatLon-filter3.txt'

    with open(filename, 'r') as in_file:
        stripped = (line.strip() for line in in_file)
        lines = (line.replace(";",",").split(",") for line in stripped if line)
        with open('log.csv', 'w') as out_file:
            writer = csv.writer(out_file)
            writer.writerows(lines)