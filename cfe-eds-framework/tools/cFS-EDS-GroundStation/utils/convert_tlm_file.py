'''
LEW-20210-1, Python Ground Station for a Core Flight System with CCSDS Electronic Data Sheets Support

Copyright (c) 2020 United States Government as represented by
the Administrator of the National Aeronautics and Space Administration.
All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''


'''
convert_tlm_file.py

This module allows a user to convert the telemtery files generated by the
Telemetry System of the cFS-EDS-Groundstation into a csv file
for a user specified Instance:Topic pair.

Command line use:
python3 convert_tlm_file.py -f <tlm_filename>         or
python3 convert_tlm_file.py --file=<tlm_filename>
'''
import sys
import getopt

import EdsLib
import CFE_MissionLib


def decode_message(mission, intf_db, raw_message):
    '''
    Decodes a raw input message into an EdsObject

    Inputs:
    mission - mission name
    intf_db - CFE_MissionLib Interface Database
    raw_message - Packed Bytes message

    Outputs:
    topic_id - The TopicId associated with the input message
    eds_entry - The EdsDb function to create the EDS object associated with the input message
    eds_object - The Unpacked EdsDb Object
    '''
    eds_id, topic_id = intf_db.DecodeEdsId(raw_message)
    eds_entry = EdsLib.DatabaseEntry(mission, eds_id)
    eds_object = eds_entry(EdsLib.PackedObject(raw_message))
    return topic_id, eds_entry, eds_object


def hex_string(string, bytes_per_line):
    '''
    Converts a hex representation of a bytes string to a more human readable format

    Inputs:
    string - hex representation of a bytes string
    bytes_per_line - Number specifying the number of hex bytes per line

    Output:
    hex_str - string that can be printed to the screen
    '''
    hex_str = ''
    count = 0
    for i in range(0, len(string), 2):
        hex_str += "0x{}{} ".format(string[i].upper(), string[i+1].upper())
        count += 1
        if count % bytes_per_line == 0:
            hex_str += '\n'
    return hex_str


def tlm_display_string(output_flag, eds_db, base_object, base_name, message=''):
    '''
    Recursive function that parses through an EDS object and generates a
    string representing an iteration of all the values contained in the object

    Inputs:
    output_flag - adusts the output string based on if printing to the screen or a csv file
    eds_db - EDS database
    base_object - An EDS object
    base_name - The starting name of the structure to appear in the display string
    message - The cumulative result of the display string (used in recursion)

    Outputs:
    result - The display string representing an iteration over all of the sub-elements
    of the input object that can be printed to the screen
    '''
    result = message
    # Array display string
    if (eds_db.IsArray(base_object)):
        for i in range(len(base_object)):
            result = tlm_display_string(output_flag, eds_db, base_object[i], f"{base_name}[{i}]", result)
    # Container display string
    elif (eds_db.IsContainer(base_object)):
        for item in base_object:
            result = tlm_display_string(output_flag, eds_db, item[1], f"{base_name}.{item[0]}", result)
    # Everything else (number, enumeration, string, etc.)
    else:
        if output_flag == 'screen':
            result += '{:<60} = {}\n'.format(base_name, base_object)
        elif output_flag == 'labels':
            result += '{}, '.format(base_name)
        elif output_flag == 'values':
            result += '{}, '.format(base_object)
        else:
            print("Something went wrong in tlm_display_string")
            result = ''

    return result


def read_packet(file_object, packet_length):
    '''
    Reads a bytes string of a particular size from a file

    Inputs:
    file_object - Python file object that contains the telemetry messages
    packet_length - The size in bytes of each telemetry message

    Output:
    packet - The packet bytes string representing a telemetry message
    '''
    while True:
        packet = file_object.read(packet_length)
        if not packet:
            break
        yield packet



def main(argv):
    """
    Gets the telemetry filename from command line arguments
    Opens up the file and reads in the message length (4 byte unsigned int)
    Reads each message, decodes it into an EDS Object, and prints the object's
    contents to a csv file of the same base name
    """
    try:
        opts, args = getopt.getopt(argv, "hs", ["file="])
    except getopt.GetoptError:
        print("convert_tlm_file.py --file=<filename>")
        sys.exit(2)

    mission = "@CFS_EDS_GS_MISSION_NAME@".lower()
    labels_printed = False
    fout = None
    screen_flag = False
    for opt, arg in opts:
        if opt == '-h':
            print("convert_tlm_file.py --file=<filename>")
            print(" --file= : telemetry file name")
            print(" -h : help")
            print(" -s : print to screen")
            sys.exit()
        elif opt in ('--file'):
            filename = arg
        elif opt == '-s':
            screen_flag = True

    try:
        # Initialize databases
        eds_db = EdsLib.Database(mission)
        intf_db = CFE_MissionLib.Database(mission, eds_db)
    except RuntimeError:
        print("convert_tlm_file.py is not properly configured")
        sys.exit(2)

    try:
        fin = open(filename, 'rb')
    except RuntimeError:
        print("Invalid file name")
        print("convert_tlm_file.py -f <filename>")
        sys.exit(2)

    packet_length = int.from_bytes(fin.read(4), byteorder='big', signed=False)
    csv_filename = filename.replace('.bin', '.csv')
    fout = open(csv_filename, 'w')

    for packet in read_packet(fin, packet_length):
        topic_id, eds_entry, eds_object = decode_message(mission, intf_db, packet)
        if not labels_printed:
            csv_string = tlm_display_string('labels', eds_db, eds_object, eds_entry.Name) + '\n'
            fout.write(csv_string)
            labels_printed = True
        csv_string = tlm_display_string('values', eds_db, eds_object, eds_entry.Name) + '\n'
        fout.write(csv_string)
        
        # Print data to the screen if desired
        if screen_flag:
            print(hex_string(packet.hex(), 16))
            print(tlm_display_string('screen', eds_db, eds_object, eds_entry.Name))

    fin.close()
    if fout is not None:
        fout.close()



if __name__ == "__main__":
    main(sys.argv[1:])
