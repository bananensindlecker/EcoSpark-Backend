from collections import defaultdict
import re
import math

def convert_to_input(transmission:str):

    #  List of all incoming instructions
    raw_instructions:list[str] = transmission.split("?")

    #  Eventual output of convert_to_input
    raw_output_instructions:list[str] = []

    #  Taking raw instructions apart into all values
    for raw_instruction in raw_instructions:
        attributes = raw_instruction.split(",")
        typee = attributes[0]

        
        if typee == "light":#  Process for light effects

            #  Pins formating for as "+Pxx / -Pxx"
            pins = attributes[1].split("/")
            pins_on_list = []
            pins_off_list = []

            for pin in pins:
                pins_on_list.append(f"+P{pin}")
                pins_off_list.append(f"-P{pin}")

            pins_on = " ".join(pins_on_list)
            pins_off = " ".join(pins_off_list)

            start:int = int(attributes[2])
            end:int = int(attributes[3])

            time_instructions: list[str] = [f"T{start} {pins_on}",f"T{end} {pins_off}"]

            #  If there is a frequency given, create blink instructions
            if len(attributes) == 5:
                frequency = math.ceil(int(attributes[4]) /2)

                blink_times:list[int] = [start + frequency]
                while blink_times[-1] + frequency < end:
                    blink_times.append(blink_times[-1]+frequency)

                blink_instructions:list[str] = []
                #  Makes the blinking happen by alternating between on and off
                for index, time in enumerate(blink_times):
                    if index % 2 == 1:
                        blink_instruction = f"T{str(time)} {pins_on}"
                        blink_instructions.append(blink_instruction)
                    if index % 2 == 0:
                        blink_instruction = f"T{str(time)} {pins_off}"
                        blink_instructions.append(blink_instruction)
                #  Add the blink instructions to the time instructions
                time_instructions.extend(blink_instructions)

            #  Add the time instructions to the raw output instructions
            raw_output_instructions.extend(time_instructions)
        elif typee == "sound":#  Process for sound effects
            filename = attributes[1]
            start:int = int(attributes[2])
            volume:int = int(attributes[3])
            time_instructions:str = f"T{start} {filename} {volume}"
            raw_output_instructions.append(time_instructions)
        elif typee == "three_d":#  Process for 3D effects

            #  Pins formating for as "+Pxx / -Pxx"
            pins = attributes[1].split("/")
            pins_on_list = []
            pins_off_list = []

            for pin in pins:
                pins_on_list.append(f"+P{pin}")
                pins_off_list.append(f"-P{pin}")

            pins_on = " ".join(pins_on_list)
            pins_off = " ".join(pins_off_list)

            start:int = int(attributes[2])
            end:int = int(attributes[3])

            time_instructions: list[str] = [f"T{start} {pins_on}",f"T{end} {pins_off}"]
            raw_output_instructions.extend(time_instructions)

    output_instructions = sort_merge_stop(raw_output_instructions)

    #  Returns the output instructions
    return output_instructions


#  Makes the magic happen
def sort_merge_stop(instructions:list[str]):
    #  Dictionary to group by T-number
    groups = defaultdict(list)

    #  Group strings by the number following 'T'
    for instruction in instructions:
        match = re.match(r"(T\d+)\s+(.*)", instruction)
        if match:
            t_num, rest = match.groups()
            groups[t_num].append(rest)

    #  Merge output
    instructions = [f"{t} {' '.join(values)}" for t, values in groups.items()]

    #  Sort output
    instructions = sorted(instructions, key=lambda x: int(x.split()[0][1:]))

    #  Adding STOP
    instructions.append(f"T{int(instructions[-1].split()[0][1:]) + 1000} stop")
    return instructions

def clean_base64(data: str) -> str:
    data = data.strip().replace('\n', '').replace('\r', '')
    #  Pad with '=' if needed
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return data


if __name__ == '__main__':
    convert_to_input("light,20,1000,2000,100")
