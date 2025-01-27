import MFRC522
import signal
import sqlite3

running = True

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
                name = input("Enter user name: ")
                c.execute("INSERT INTO attendance (uid, name, present) VALUES (?, ?, ?)", (uidToString(uid), name, True))
                print("RFID: %s, Name: %s, Status: Present" % (uidToString(uid), name))

            conn.commit()
            conn.close()

        else:
            print("Authentication error")
