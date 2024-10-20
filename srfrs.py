#!/usr/bin/env python3
# Original Authors: Fred (W6BSD), SR-FRS by BG7IYN
# Changelog:
#   10/20/2024 
#   - added docstrings
#   - graceful port connection detection
#   - ensure Missing func Attribute in 
#     Subcommands doesn't crash script
#   - complete the set filters logic
#   - add --probe argument to see if we can 
#     get settings from radio
#   - saves settings to json file so parameters 
#     can be optional once you have a good 
#     configuration recorded
#

__doc__ = """srfrs"""

import argparse
import logging
import os
import sys
import textwrap
import time
import json
import serial

logging.basicConfig(format='%(name)s: %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('SRFRS')


CTCSS = (
  "None", "67.0", "71.9", "74.4", "77.0", "79.7", "82.5", "85.4", "88.5", "91.5",
  "94.8", "97.4", "100.0", "103.5", "107.2", "110.9", "114.8", "118.8", "123.0",
  "127.3", "131.8", "136.5", "141.3", "146.2", "151.4", "156.7", "162.2",
  "167.9", "173.8", "179.9", "186.2", "192.8", "203.5", "210.7", "218.1",
  "225.7", "233.6", "241.8", "250.3"
)

DCS_CODES = [
  "023", "025", "026", "031", "032", "036", "043", "047", "051", "053", "054", "065", "071",
  "072", "073", "074", "114", "115", "116", "122", "125", "131", "132", "134", "143", "145",
  "152", "155", "156", "162", "165", "172", "174", "205", "212", "223", "225", "226", "243",
  "244", "245", "246", "251", "252", "255", "261", "263", "265", "266", "271", "274", "306",
  "311", "315", "325", "331", "332", "343", "346", "351", "356", "364", "365", "371", "411",
  "412", "413", "423", "431", "432", "445", "446", "452", "454", "455", "462", "464", "465",
  "466", "503", "506", "516", "523", "526", "532", "546", "565", "606", "612", "624", "627",
  "631", "632", "654", "662", "664", "703", "712", "723", "731", "732", "734", "743", "754"
]

DEFAULT_BAUDRATE = 9600

class SRFRS:
  EOL = "\r\n"
  INIT = "AT+DMOCONNECT"
  SETGRP = "AT+DMOSETGROUP"
  FILTER = "AT+SETFILTER"
  VOLUME = "AT+DMOSETVOLUME"
  TAIL = "AT+SETTAIL"
  NARROW = 0
  WIDE = 1
  PORTS = ('/dev/serial0', '/dev/ttyUSB0', 'COM1', 'COM2', 'COM3', 'COM4')
  READ_TIMEOUT = 1.0

  def __init__(self, port=None):
    self.serial = None
    if port:
      ports = [port]
    else:
      ports = self.PORTS

    for _port in ports:
      try:
        self.serial = serial.Serial(port=_port, 
                                    baudrate=DEFAULT_BAUDRATE,
                                    parity=serial.PARITY_NONE, 
                                    stopbits=serial.STOPBITS_ONE,
                                    bytesize=serial.EIGHTBITS,
                                    timeout=self.READ_TIMEOUT)
        logger.info(f"Successfully opened port: {_port}")  
        break
      except serial.SerialException as err:
        logger.debug(f"Failed to open port {_port}")

    if not isinstance(self.serial, serial.Serial):
      raise IOError('Error opening the serial port')

    self.send(self.INIT)
    reply = self.readline()
    if reply != "+DMOCONNECT:0":
      raise SystemError('Connection error')
    else:
      logger.info(f"Found device on {_port}")  


    # Load settings from file
    self.load_settings()

  

  def close(self):
    self.serial.close()

  def send(self, *args):
    """
    Sends a command to the connected serial device.

    This method formats the provided arguments into a single string command,
    appends the end-of-line (EOL) sequence, and sends the resulting data over
    the serial connection. If there is an issue with the serial communication,
    an error is logged.

    Args:
        *args: Arbitrary string arguments representing the command and its parameters
               to be sent to the serial device. They will be joined by commas.

    Raises:
        serial.SerialException: If writing to the serial port fails, this exception is caught,
                                and the error is logged without interrupting the flow.

    Example:
        self.send("AT+DMOSETGROUP", "1", "145.0000", "145.0000", "00", "4", "00", "1")
    """

    data = ','.join(args)
    logger.debug('Sending: %s', data)
    data = bytes(data + self.EOL, 'ascii')
    try:
        self.serial.write(data)
    except serial.SerialException as err:
        logger.error(f"Failed to send data to serial port: {err}")

  def readline(self):

    """
    Reads a line of response from the connected serial device.

    This method attempts to read a line of data from the serial port, decodes
    it from ASCII, and removes any trailing whitespace characters. If an issue 
    occurs during the reading process, a warning is logged, and the method 
    returns None.

    Returns:
        str: The decoded and stripped line of response from the serial device.
        None: If a SerialException occurs during the read operation.

    Raises:
        serial.SerialException: If reading from the serial port fails, the exception is caught,
                                a warning is logged, and the method returns None.

    Example:
        response = self.readline()
    """

    try:
        line = self.serial.readline()
    except serial.SerialException as err:
        logger.warning(f"Failed to read from serial port: {err}")
        return None
    line = line.decode('ascii')
    logger.debug(line)
    return line.rstrip()

  def version(self):

    """
    Requests and retrieves the firmware version of the connected serial device.

    This method sends a command to query the firmware version of the device 
    and waits for a response. The response is expected to be in the format 
    `+DMOVERQ:<version>`. If the response is properly formatted, the version 
    number is extracted and logged. If the response cannot be parsed, an 
    error is logged.

    Returns:
        str: The firmware version of the device, if successfully retrieved.
        None: If the response could not be parsed or no valid response is received.

    Raises:
        ValueError: If the response is not in the expected format and cannot 
                    be split into the expected parts.

    Example:
        firmware_version = self.version()
    """

    self.send("AT+DMOVERQ")
    time.sleep(0.5)
    reply = self.readline()
    try:
      _, version = reply.split(':')
    except ValueError:
      logger.error('Unable to decode the firmeare version')
    else:
      logger.info('Firmware version: %s', version)
    return version

  def get_radio_settings(self):
    """
    Queries and returns the current radio settings (frequency, squelch, tone, etc.).

    This function sends a command to the radio to retrieve the current settings, such as
    the receive and transmit frequencies, squelch level, CTCSS or DCS tone, and wide/narrow mode.
    The response is parsed and returned in a structured format. If the response indicates an error
    or cannot be parsed, an error is logged.

    Returns:
        dict: A dictionary containing the current radio settings, including:
            - 'rx_freq': The receive frequency in MHz.
            - 'tx_freq': The transmit frequency in MHz.
            - 'squelch': The current squelch level.
            - 'tone': The CTCSS or DCS tone in use, if any.
            - 'mode': The mode (wide or narrow).

    Raises:
        ValueError: If the response from the radio cannot be parsed.

    Example:
        settings = self.get_radio_settings()
        print(settings)  # {'rx_freq': 145.500, 'tx_freq': 145.500, 'squelch': 4, 'tone': '100.0', 'mode': 'wide'}
    """
    self.send("AT+DMOGETGROUP")  # Example command for getting settings; replace with the correct command
    time.sleep(1)
    response = self.readline()

    if response is None or not response.startswith("+DMOGETGROUP:"):
        logger.error("Failed to retrieve radio settings")
        logger.info( response )
        return None

    try:
        # Example of parsing response; adjust this to match actual response format
        _, mode, tx_freq, rx_freq, tone, squelch, _, _ = response.split(',')
        mode = 'wide' if mode == '1' else 'narrow'
        tone_value = CTCSS[int(tone)] if tone != '00' else 'None'
        
        return {
            'rx_freq': float(rx_freq),
            'tx_freq': float(tx_freq),
            'squelch': int(squelch),
            'tone': tone_value,
            'mode': mode
        }
    except ValueError:
        logger.error("Unable to parse the radio settings response")
        return None


  def set_radio(self, opts):

    """
    Configures the radio with the specified frequency, tone, and squelch settings.

    This method sets up the radio parameters such as the receive and transmit 
    frequencies, CTCSS or DCS tone, squelch level, and the wide/narrow mode. It 
    also handles cases where an offset is specified to adjust the transmit frequency. 
    The command is sent to the serial device, and the method waits for a confirmation 
    response. If the response indicates a successful operation, the configuration 
    is logged. Otherwise, an error is logged.

    Args:
        opts (Namespace): An argparse Namespace object containing the following attributes:
            - frequency (float): The receive frequency in MHz.
            - offset (float): The frequency offset in MHz for transmit frequency (default 0.0).
            - squelch (int): The squelch level (0 to 8).
            - ctcss (str or None): The CTCSS tone, if specified.
            - dcs (str or None): The DCS code, if specified.
            - close_tail (bool or None): Whether to close the CTCSS tail tone.

    Raises:
        SystemError: If the device responds with an error code for the programming command.
        ValueError: If the CTCSS or DCS tone cannot be properly decoded or applied.

    Example:
        opts = Namespace(frequency=145.000, offset=0.6, squelch=4, ctcss="100.0", dcs=None)
        self.set_radio(opts)
    """

    tone = opts.ctcss if opts.ctcss else opts.dcs
    if not tone:                # 00 = No ctcss or dcs tone
      tone = '00'

    if opts.offset == 0.0:
      tx_freq = rx_freq = "{:.4f}".format(opts.frequency)
    else:
      rx_freq = "{:.4f}".format(opts.frequency)
      tx_freq = "{:.4f}".format(opts.frequency + opts.offset)

    cmd = "{}={},{},{},{},{},{},{}".format(self.SETGRP, self.WIDE, tx_freq, rx_freq,
                                        tone, opts.squelch, tone,1)
    self.send(cmd)
    time.sleep(1)
    response = self.readline()
    if response != '+DMOSETGROUP:0':
      logger.error('SR-FRS programming error')
    else:
      # Update current settings dictionary
      self.current_settings['frequency'] = opts.frequency
      self.current_settings['offset'] = opts.offset
      self.current_settings['squelch'] = opts.squelch
      self.current_settings['ctcss'] = opts.ctcss
      self.current_settings['dcs'] = opts.dcs
      self.save_settings()
      logger.info(f"Current settings updated: {self.current_settings}")

      if opts.ctcss:
        msg = "%s, RX frequency: %s, TX frequency: %s, ctcss: %s, squelch: %s, OK"
        tone = CTCSS[int(tone)]
        logger.info(msg, response, rx_freq, tx_freq, tone, opts.squelch)
      elif opts.dcs:
        msg = "%s, RX frequency: %s, TX frequency: %s, dcs: %s, squelch: %s, OK"
        logger.info(msg, response, rx_freq, tx_freq, tone, opts.squelch)
      else:
        msg = "%s, RX frequency: %s, TX frequency: %s, squelch: %s, OK"
        logger.info(msg, response, rx_freq, tx_freq, opts.squelch)
      
    if opts.close_tail is not None and opts.ctcss is not None:
      self.close_tail(opts)
    elif opts.close_tail is not None:
      logger.warning('Ignoring "--close-tail" specified without ctcss')

  def set_filter(self, opts):
    """
    Configures the radio's audio filters, including pre-emphasis, high-pass, and low-pass filters.

    This method sends a command to set or disable various audio filters on the radio.
    The filters include [Pre/De]-emphasis, high-pass, and low-pass. Each filter can
    be enabled or disabled based on the `opts` values. The method waits for a confirmation
    response from the device and logs the result of the operation.

    Args:
        opts (Namespace): An argparse Namespace object containing the following attributes:
            - emphasis (bool): Whether to enable pre-emphasis (True) or disable it (False).
            - highpass (bool): Whether to enable the high-pass filter (True) or disable it (False).
            - lowpass (bool): Whether to enable the low-pass filter (True) or disable it (False).

    Raises:
        SystemError: If the device responds with an error code when setting the filters.

    Example:
        opts = Namespace(emphasis=True, highpass=False, lowpass=True)
        self.set_filter(opts)
    """
    _yn = {True: "Yes", False: "No"}
    # filters are pre-emphasis, high-pass, low-pass
    cmd = "{}={},{},{}".format(self.FILTER, int(not opts.emphasis),
                               int(not opts.highpass), int(not opts.lowpass))
    self.send(cmd)
    time.sleep(1)
    response = self.readline()
    if response != "+DMOSETFILTER:0":
      logger.error('SRFRS set filter error')
    else:
      # Update current settings dictionary
      self.current_settings['filter'] = {
          'emphasis': opts.emphasis,
          'highpass': opts.highpass,
          'lowpass': opts.lowpass
      }      
      logger.info("%s filters [Pre/De]emphasis: %s, high-pass: %s, low-pass: %s",
                  response, _yn[opts.emphasis], _yn[opts.highpass], _yn[opts.lowpass])

  def set_volume(self, opts):
    """
    Sets the volume level of the radio.

    This method sends a command to the radio to set the volume level. The volume 
    level should be an integer between 1 and 8. The method waits for a confirmation 
    response from the device and logs the result. If the volume level is set 
    successfully, it logs the success message; otherwise, it logs an error.

    Args:
        opts (Namespace): An argparse Namespace object containing the following attribute:
            - level (int): The desired volume level (1 to 8).

    Raises:
        SystemError: If the device responds with an error code when setting the volume.

    Example:
        opts = Namespace(level=5)
        self.set_volume(opts)
    """
    cmd = "{}={:d}".format(self.VOLUME, opts.level)
    self.send(cmd)
    time.sleep(1)
    response = self.readline()
    if response != "+DMOSETVOLUME:0":
      logger.error('SR-FRS set volume error')
    else:
      # Update current settings dictionary
      self.current_settings['volume'] = opts.level
      logger.info("%s Volume level: %d, OK", response, opts.level)

  def close_tail(self, opts):
    """
    Configures the CTCSS tail tone closing behavior on the radio.

    This method sends a command to enable or disable the closing of the CTCSS tail tone
    (also known as the "tail squelch"). The command is based on the value of `close_tail` 
    provided in the options. The method waits for a confirmation response from the device 
    and logs the result of the operation.

    Args:
        opts (Namespace): An argparse Namespace object containing the following attribute:
            - close_tail (bool): Whether to enable (True) or disable (False) the closing 
                                 of the CTCSS tail tone.

    Raises:
        SystemError: If the device responds with an error code when setting the tail tone behavior.

    Example:
        opts = Namespace(close_tail=True)
        self.close_tail(opts)
    """

    _yn = {True: "Yes", False: "No"}
    cmd = "{}={}".format(self.TAIL, int(opts.close_tail))
    self.send(cmd)
    time.sleep(1)
    response = self.readline()
    if response != "+DMOSETTAIL:0":
      logger.error('SRFRS set filter error')
    else:
      logger.info("%s close tail: %s", response, _yn[opts.close_tail])

  def get_current_settings(self):
      """
      Returns the last applied settings.

      This method retrieves the last known settings applied to the radio, including frequency,
      squelch, volume, CTCSS/DCS tones, and filter settings.

      Returns:
          dict: A dictionary with the last applied settings.
      """
      return self.current_settings
  import json

  def save_settings(self):
      """
      Saves the current settings to a file (settings.json).
      """
      with open('settings.json', 'w') as file:
          json.dump(self.current_settings, file)
      logger.info("Settings saved to settings.json")

  def load_settings(self):
      """
      Loads the settings from a file (settings.json) if it exists.
      If the file doesn't exist, it initializes with default settings.
      """
      try:
          with open('settings.json', 'r') as file:
              self.current_settings = json.load(file)
          logger.info("Settings loaded from settings.json")
      except FileNotFoundError:
          logger.warning("Settings file not found. Using default settings.")
          self.current_settings = {
              'frequency': None,
              'offset': None,
              'squelch': None,
              'ctcss': None,
              'dcs': None,
              'volume': None,
              'filter': None
          }



  def probe_device(self):
    """
    Probes the radio device with a series of potential AT commands to check if they are supported.

    This function sends a set of common and speculative AT commands to the radio to identify
    which commands are recognized and supported by the device. It logs the responses for each command
    and whether the command is likely supported.

    Returns:
        dict: A dictionary with command names as keys and boolean values indicating support status.

    Example:
        supported_commands = self.probe_device()
        print(supported_commands)
    """
    # List of potential commands to probe
    commands_to_probe = [
        "AT+DMOGETGROUP?",      # Query group settings (hypothetical)
        "AT+DMOGETGROUP=?",      # Query group settings (hypothetical)
        "AT+DMOGETGROUP",       # Set group settings
        "AT+DMOSETGROUP?",      # Query group settings (hypothetical)
        "AT+DMOSETGROUP=?",      # Query group settings (hypothetical)
        "AT+DMOSETGROUP",       # Set group settings
        "AT+DMOVERQ?",          # Request firmware version
        "AT+DMOLIST?",          # List supported commands (hypothetical)
        "AT+DMOHELP?",          # Query help menu
        "AT+DMOSTORE?",         # Check if the settings can be stored
        "AT+DMOLOAD?",          # Query or load saved settings
        "AT+DMOFACTORYRESET?",  # Factory reset command
        "AT+DMODEBUGON?",       # Enable debug mode (hypothetical)
        "AT+DMODEBUGOFF?",      # Disable debug mode (hypothetical)
        "AT+DMONOTIFY?",        # Enable or check notifications
        "AT+DMOINFO?",          # Query general information
        "AT+DMOGETPOWER?",      # Query current power level
        "AT+DMOGETFREQ?",       # Query current frequency settings
        "AT+DMODEBUG?",         # General debug inquiry
        "AT+CIPSTATUS",         # current connection status
    ]



    supported_commands = {}

    for command in commands_to_probe:
        logger.info(f"Probing command: {command}")
        self.send(command)
        time.sleep(1)  # Give the device some time to respond
        response = self.readline()
        
        if response is None or "ERROR" in response:
            # logger.warning(f"Command not supported: {command}")
            supported_commands[command] = False
        else:
            logger.info(f"Command supported: {command}, Response: {response}")
            supported_commands[command] = True

    return supported_commands


def type_frequency(parg):
  """
  Validates and converts the provided frequency argument.

  This function takes a string input, converts it to a float, and checks if the 
  frequency is within the valid amateur radio bands (136-174 MHz or 400-470 MHz). 
  If the frequency is valid, it returns the frequency as a float. If the frequency 
  is outside the allowed ranges or cannot be converted to a float, an error is logged 
  and an argparse.ArgumentTypeError is raised.

  Args:
      parg (str): The frequency value as a string input to be validated.

  Returns:
      float: The validated frequency in MHz if it is within the valid ranges.

  Raises:
      argparse.ArgumentTypeError: If the input cannot be converted to a float or if 
                                  the frequency is outside the valid amateur bands.

  Example:
      frequency = type_frequency("145.500")  # Returns 145.500 if valid
  """

  try:
    frequency = float(parg)
  except ValueError:
    raise argparse.ArgumentTypeError from None

  if not 136 < frequency < 174 and not 400 < frequency < 470:
    logger.error('Frequency outside the amateur bands')
    raise argparse.ArgumentError
  return frequency

def type_ctcss(parg):
  """
  Validates and converts the provided CTCSS tone value.

  This function takes a string input representing a CTCSS tone and checks if it is a valid 
  CTCSS tone from the predefined list. If valid, the corresponding index is returned as a 
  zero-padded string representing the CTCSS tone code. If the input cannot be converted to 
  a valid CTCSS tone, an error is logged and an argparse.ArgumentTypeError is raised.

  Args:
      parg (str): The CTCSS tone value as a string to be validated (e.g., "100.0").

  Returns:
      str: The zero-padded CTCSS tone code (e.g., "13" for "100.0").

  Raises:
      argparse.ArgumentTypeError: If the input cannot be converted to a float or if 
                                  the CTCSS tone is not found in the list of valid tones.

  Example:
      ctcss_code = type_ctcss("100.0")  # Returns "13" for the CTCSS tone "100.0"
  """  
  err_msg = 'Invalid CTCSS use the --help argument for the list of CTCSS'
  try:
    ctcss = str(float(parg))
  except ValueError:
    raise argparse.ArgumentTypeError from None

  if ctcss not in CTCSS:
    logger.error(err_msg)
    raise argparse.ArgumentError

  tone_code = CTCSS.index(ctcss)
  cc="{:02d}".format(int(tone_code))
  print (cc)
  return "{:02d}".format(int(tone_code))

def type_dcs(parg):
  """
  Validates and converts the provided DCS code value.

  This function takes a string input representing a DCS (Digital Coded Squelch) code 
  and checks if it is a valid DCS code from the predefined list. The input should 
  end with either 'N' (Normal) or 'I' (Inverse) to specify the direction of the code. 
  If valid, the function returns the formatted DCS code. If the input is invalid, 
  an error is logged and an argparse.ArgumentTypeError is raised.

  Args:
      parg (str): The DCS code as a string, which must end with 'N' or 'I' (e.g., "047I").

  Returns:
      str: The validated and formatted DCS code (e.g., "047N" or "047I").

  Raises:
      argparse.ArgumentTypeError: If the input cannot be validated as a proper DCS code or 
                                  if the code is not found in the list of valid codes.

  Example:
      dcs_code = type_dcs("047I")  # Returns "047I" if valid
  """  
  err_msg = 'Invalid DCS use the --help argument for the list of DCS'
  if parg[-1] not in ('N', 'I'):
    raise argparse.ArgumentError

  code, direction = parg[:-1], parg[-1]
  try:
    dcs = "{:03d}".format(int(code))
  except ValueError:
    raise argparse.ArgumentTypeError from None

  if dcs not in DCS_CODES:
    logger.error(err_msg)
    raise argparse.ArgumentError

  dcs_code = dcs + direction
  return "{:s}".format(dcs_code)

def type_squelch(parg):
  """
  Validates and converts the provided squelch value.

  This function takes a string input representing a squelch level and converts it to 
  an integer. The squelch level must be within the valid range of 0 to 8 (inclusive). 
  If the input is a valid integer and within the allowed range, the function returns 
  the integer value. If the input is invalid or out of range, an error is logged and 
  an argparse.ArgumentTypeError is raised.

  Args:
      parg (str): The squelch value as a string (e.g., "4").

  Returns:
      int: The validated squelch level as an integer (0 to 8).

  Raises:
      argparse.ArgumentTypeError: If the input cannot be converted to an integer or if 
                                  the value is outside the range of 0 to 8.

  Example:
      squelch_level = type_squelch("4")  # Returns 4 if valid
  """  
  try:
    value = int(parg)
  except ValueError:
    raise argparse.ArgumentTypeError from None

  if value not in range(0, 9):
    logger.error('The value must must be between 0 and 8 (inclusive)')
    raise argparse.ArgumentError
  return value

def type_level(parg):
  """
  Validates and converts the provided volume level.

  This function takes a string input representing a volume level and converts it 
  to an integer. The volume level must be within the valid range of 1 to 8 
  (inclusive). If the input is a valid integer and within the allowed range, 
  the function returns the integer value. If the input is invalid or out of range, 
  an error is logged and an argparse.ArgumentTypeError is raised.

  Args:
      parg (str): The volume level as a string (e.g., "5").

  Returns:
      int: The validated volume level as an integer (1 to 8).

  Raises:
      argparse.ArgumentTypeError: If the input cannot be converted to an integer or if 
                                  the value is outside the range of 1 to 8.

  Example:
      volume_level = type_level("5")  # Returns 5 if valid
  """  
  try:
    value = int(parg)
  except ValueError:
    raise argparse.ArgumentTypeError from None

  if value not in range(1, 9):
    logger.error('The value must must be between 1 and 8 (inclusive)')
    raise argparse.ArgumentError
  return value

def yesno(parg):
  yes_strings = ["y", "yes", "true", "1", "on"]
  no_strings = ["n", "no", "false", "0", "off"]
  if parg.lower() in yes_strings:
    return True
  if parg.lower() in no_strings:
    return False
  raise argparse.ArgumentError

def noneyesno(parg):
  if parg is not None:
    return yesno(parg)

def set_loglevel():
  """
  Configures the logging level based on the environment variable 'LOGLEVEL'.

  This function retrieves the log level from the environment variable 'LOGLEVEL'. 
  If the variable is set, it attempts to configure the logger to use the specified 
  log level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR'). If 'LOGLEVEL' is not set, 
  the log level defaults to 'INFO'. If the log level is invalid, a warning is logged, 
  and the default level remains in effect.

  Raises:
      ValueError: If the specified 'LOGLEVEL' is not a valid logging level, this is caught, 
                  and a warning is logged.

  Example:
      os.environ['LOGLEVEL'] = 'DEBUG'
      set_loglevel()  # Configures the logger to use DEBUG level
  """  
  loglevel = os.getenv('LOGLEVEL', 'INFO')
  loglevel = loglevel.upper()
  try:
    logger.root.setLevel(loglevel)
  except ValueError:
    logger.warning('Loglevel error: %s', loglevel)

def format_codes():
  """
  Formats and returns a list of CTCSS and DCS codes for display.

  This function generates a formatted string containing both the CTCSS (Continuous 
  Tone-Coded Squelch System) codes and the DCS (Digital Coded Squelch) codes, making 
  them easier to display in the help text of a command-line tool. The CTCSS codes are 
  presented first, followed by the DCS codes, which include a note indicating that 
  DCS codes must be followed by 'N' (Normal) or 'I' (Inverse).

  Returns:
      str: A formatted string with CTCSS codes and DCS codes, ready for display.

  Example:
      codes = format_codes()
      print(codes)  # Outputs the formatted list of CTCSS and DCS codes
  """  
  ctcss = textwrap.wrap(', '.join(CTCSS[1:]))
  dcs = textwrap.wrap(', '.join(DCS_CODES))

  codes = (
    "CTCSS codes (PL Tones):\n{}".format('\n'.join(ctcss)),
    "\n\n",
    "DCS Codes:\n"
    "DCS codes must be followed by N or I for Normal or Inverse:\n",
    "> Example: 047I\n"
    "{}".format('\n'.join(dcs))
  )
  return ''.join(codes)


def main():
    set_loglevel()

    # First, parse global arguments like --debug
    global_parser = argparse.ArgumentParser(
        description="SR-FRS by BG7IYN",
        epilog=format_codes(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    global_parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode")
    global_parser.add_argument("--port", type=str, help="Serial port [default: linux console port]")
    global_parser.add_argument("--probe", action="store_true", default=False, help="Probe the device for supported AT commands")

    # Now, parse only global arguments
    global_args, remaining_args = global_parser.parse_known_args()

    # Set log level if debug is enabled
    if global_args.debug:
        logger.setLevel(logging.DEBUG)

    # Create subparser for subcommands
    subparsers = global_parser.add_subparsers()

    p_radio = subparsers.add_parser("radio", help='Program the radio (frequency/tone/squelch)')
    p_radio.set_defaults(func="radio")
    p_radio.add_argument("--frequency", type=type_frequency, help="Receive frequency. Will use saved setting if not provided.")
    p_radio.add_argument("--offset", type=float, help="Offset in MHz, 0 for no offset. Will use saved setting if not provided.")
    p_radio.add_argument("--squelch", type=type_squelch, help="Squelch value (0 to 8). Will use saved setting if not provided.")

    # Mutually exclusive CTCSS or DCS
    code_group = p_radio.add_mutually_exclusive_group()
    code_group.add_argument("--ctcss", type=type_ctcss, help="CTCSS (PL Tone) 0 for no CTCSS. Will use saved setting if not provided.")
    code_group.add_argument("--dcs", type=type_dcs, help=("DCS code must be the number followed by [N normal] or [I inverse]. Will use saved setting if not provided."))

    p_radio.add_argument("--close-tail", type=noneyesno, help="Close CTCSS Tail Tone (yes/no).")

    p_volume = subparsers.add_parser("volume", help="Set the volume level")
    p_volume.set_defaults(func="volume")
    p_volume.add_argument("--level", type=type_level, help="Volume value (1 to 8). Will use saved setting if not provided.")

    p_filter = subparsers.add_parser("filters", help="Set/Unset filters")
    p_filter.set_defaults(func="filters")
    p_filter.add_argument("--emphasis", type=yesno, help="Disable [Pr/De]-emphasis (yes/no). Will use saved setting if not provided.")
    p_filter.add_argument("--highpass", type=yesno, help="Disable high pass filter (yes/no). Will use saved setting if not provided.")
    p_filter.add_argument("--lowpass", type=yesno, help="Disable low pass filters (yes/no). Will use saved setting if not provided.")

    p_version = subparsers.add_parser("version", help="Show the firmware version of the SRFRS")
    p_version.set_defaults(func="version")

    # Parse the remaining subcommand arguments
    subcommand_args = global_parser.parse_args(remaining_args)

    # Handle Missing func Attribute in Subcommands
    if not hasattr(subcommand_args, 'func'):
        logger.error("A subcommand is required (radio, volume, filters, version). Use --help for more details.")
        sys.exit(1)

    logger.debug(global_args)
    logger.debug(subcommand_args)

    try:
        radio = SRFRS(global_args.port)
    except (IOError, SystemError) as err:
        logger.error(err)
        sys.exit(1)

    # Run the probe if --probe argument is passed
    if global_args.probe:
        supported_commands = radio.probe_device()
        logger.info(f"Supported commands: {supported_commands}")
        return  # Exit after probing, no further action

    # Use saved settings if not provided via command-line arguments
    current_settings = radio.get_current_settings()

    if subcommand_args.func == 'radio':
        subcommand_args.frequency = subcommand_args.frequency or current_settings.get('frequency')
        subcommand_args.offset = subcommand_args.offset or current_settings.get('offset', 0.0)
        subcommand_args.squelch = subcommand_args.squelch or current_settings.get('squelch', 4)
        subcommand_args.ctcss = subcommand_args.ctcss or current_settings.get('ctcss')
        subcommand_args.dcs = subcommand_args.dcs or current_settings.get('dcs')
        
        radio.set_radio(subcommand_args)

    elif subcommand_args.func == 'filters':
        subcommand_args.emphasis = subcommand_args.emphasis if subcommand_args.emphasis is not None else current_settings.get('filter', {}).get('emphasis', False)
        subcommand_args.highpass = subcommand_args.highpass if subcommand_args.highpass is not None else current_settings.get('filter', {}).get('highpass', False)
        subcommand_args.lowpass = subcommand_args.lowpass if subcommand_args.lowpass is not None else current_settings.get('filter', {}).get('lowpass', False)

        radio.set_filter(subcommand_args)

    elif subcommand_args.func == 'volume':
        subcommand_args.level = subcommand_args.level or current_settings.get('volume', 4)
        radio.set_volume(subcommand_args)

if __name__ == "__main__":
    main()

