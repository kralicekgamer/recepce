import MFRC522
import signal
import sqlite3

running = True

def uidToString(uid):
    mystring = ""
    for i in uid:
        mystring = format(i, '02X') + mystring
    return mystring

def end_read(signal, frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    exit()

signal.signal(signal.SIGINT, end_read)

MIFAREReader = MFRC522.MFRC522()


while running:
    (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

    if status == MIFAREReader.MI_OK:
        print ("Card detected")
        (status, uid) = MIFAREReader.MFRC522_SelectTagSN()
        if status == MIFAREReader.MI_OK:
            print("Card read UID: %s" % uidToString(uid))

            conn = sqlite3.connect('attendance.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS attendance
                         (uid TEXT PRIMARY KEY, present BOOLEAN)''')
            c.execute("SELECT present FROM attendance WHERE uid=?", (uidToString(uid),))
            row = c.fetchone()

            if row:
                new_status = not row[0]
                c.execute("UPDATE attendance SET present=? WHERE uid=?", (new_status, uidToString(uid)))
            else:
                c.execute("INSERT INTO attendance (uid, present) VALUES (?, ?)", (uidToString(uid), True))

            if row:
                print("Presence status updated to: %s" % ("Present" if new_status else "Absent"))
            else:
                print("New card added with status: Present")

            conn.commit()
            conn.close()

        else:
            print("Authentication error")
