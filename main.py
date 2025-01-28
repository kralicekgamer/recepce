import MFRC522
import signal
import sqlite3
import smbus2
import time
import curses

I2C_ADDR = 0x27
LCD_WIDTH = 16  

LCD_CHR = 1
LCD_CMD = 0

LCD_LINE_1 = 0x80 
LCD_LINE_2 = 0xC0 

LCD_BACKLIGHT = 0x08  
ENABLE = 0b00000100

running = True

def lcd_init(bus):
    """Inicializace LCD displeje"""
    lcd_byte(bus, 0x33, LCD_CMD)
    lcd_byte(bus, 0x32, LCD_CMD)
    lcd_byte(bus, 0x06, LCD_CMD)
    lcd_byte(bus, 0x0C, LCD_CMD)
    lcd_byte(bus, 0x28, LCD_CMD)
    lcd_clear(bus)

def lcd_byte(bus, bits, mode):
    """Odeslání dat na LCD"""
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT

    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bus, bits_high)

    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bus, bits_low)

def lcd_toggle_enable(bus, bits):
    """Aktivace enable signálu"""
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_clear(bus):
    """Vyčištění LCD"""
    lcd_byte(bus, 0x01, LCD_CMD)
    time.sleep(0.002)

def lcd_message(bus, message):
    """Zobrazení zprávy na LCD"""
    message = message.ljust(LCD_WIDTH, " ")
    for i in range(LCD_WIDTH):
        lcd_byte(bus, ord(message[i]), LCD_CHR)

def get_name(stdscr):
    bus = smbus2.SMBus(1)
    lcd_init(bus)

    curses.noecho() 
    curses.cbreak()
    stdscr.nodelay(False)  

    stdscr.clear()
    stdscr.refresh()

    user_input = ""

    while True:
        key = stdscr.getch()

        if key == 10: 
            print(user_input)  
            lcd_clear(bus)  
            return user_input

        elif key == 127:
            user_input = user_input[:-1]
        elif 32 <= key <= 126: 
            user_input += chr(key)

        lcd_clear(bus)
        lcd_byte(bus, LCD_LINE_1, LCD_CMD)
        lcd_message(bus, user_input[-LCD_WIDTH:]) 

def uidToString(uid):
    mystring = ""
    for i in uid:
        mystring = format(i, '02X') + mystring
    return mystring

def end_read(_signal, _frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    exit()

signal.signal(signal.SIGINT, end_read)

MIFAREReader = MFRC522.MFRC522()

while running:
    (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

    if status == MIFAREReader.MI_OK:
        print("Card detected")
        (status, uid) = MIFAREReader.MFRC522_SelectTagSN()
        if status == MIFAREReader.MI_OK:
            print("Card read UID: %s" % uidToString(uid))

            conn = sqlite3.connect('attendance.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS attendance
                        (uid TEXT PRIMARY KEY, name TEXT, present BOOLEAN)''')
            c.execute("SELECT name, present FROM attendance WHERE uid=?", (uidToString(uid),))
            row = c.fetchone()

            if row:
                new_status = not row[1]
                c.execute("UPDATE attendance SET present=? WHERE uid=?", (new_status, uidToString(uid)))
                print("RFID: %s, Name: %s, Status: %s" % (uidToString(uid), row[0], "Present" if new_status else "Absent"))
            else:
                name = curses.wrapper(get_name)
                c.execute("INSERT INTO attendance (uid, name, present) VALUES (?, ?, ?)", (uidToString(uid), name, True))
                print("RFID: %s, Name: %s, Status: Present" % (uidToString(uid), name))

            conn.commit()
            conn.close()

        else:
            print("Authentication error")