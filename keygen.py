#!/usr/bin/env python
import sys
import signal
import logging
import base64
import time
import sqlite3
from M2Crypto import RSA
from threading import Event

DB_FILE = "keystore.db"
STRENGTH = 1024
EXPONENT = 65537

exit = Event()

## TODO should keys be encrypted????  Probably.

def gen_keys(count=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        for i in xrange(count):
            if exit.is_set(): 
                logging.info("Interrupted!")
                break
            priv = RSA.gen_key(STRENGTH,EXPONENT)
            priv_pem = priv.as_pem(cipher=None)
            pub_pem = RSA.new_pub_key(priv.pub()).as_pem(cipher=None)
            c.execute('insert into device_keys (public_key,private_key) values (?,?)',(pub_pem,priv_pem))
        conn.commit()
        logging.info("Generated %d  %d-bit RSA key pairs to %s", i+1, STRENGTH, DB_FILE)
    except:
        logging.exception("Error while generating keys!")
        conn.rollback()
    finally:
        c.close()
        conn.close()


def issue_private_key(mac=None):
    '''
    Returns the next unused private key as a tuple in the form (key_id, PEM_string)
    Use like so:
    id, key = keygen.issue_private_key()
    # write key to the target device
    mac = '' # get the MAC from the target device
    keygen.record_key_used(id, mac) # this updates the database
    '''
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        if mac:
            row = c.execute('select id,private_key from device_keys where issued_to_mac=? limit 1',
                    (mac,)).fetchone()
            if row: # return an already-issued key for this MAC if one has been given
                id_, key = row
                return id_, key 

        row = c.execute('select id,private_key from device_keys where issued=0 limit 1',()).fetchone()
        if row is None:
            raise Exception("No more unused keys!")

        id_, key = row
        c.execute('update device_keys set issued=1 where id=?',(id_,)) # make sure this doesn't get issued again.
        logging.debug("Issuing key %d", id_)
        conn.commit()
        return (id_, key)
    except:
        logging.exception("Error while issuing key!")
        conn.rollback()
    finally:
        c.close()
        conn.close()
    

def record_key_used(id_, mac):
    '''
    Record that a private key was issued to the given device
    '''
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        issue_date = time.time()
        c.execute( 'update device_keys set issued_to_mac=?, issued_date=? where id=?',
                (mac, issue_date, id_) )

        if c.rowcount != 1:
            raise Exception("Couldn't update key ID: "+ id_)
        conn.commit()
    except:
        logging.exception("Error while issuing key!")
        conn.rollback()
    finally:
        c.close()
        conn.close()


def write_pem_file(file_name='device_private_key.pem'):
    '''
    Write a private key to a file in PEM format
    Mostly used for testing purposes.
    '''
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        row = c.execute('select id,private_key from device_keys where issued=0 limit 1',()).fetchone()
        if row is None:
            raise Exception("No more unused keys!")

        id_, key = row
        with open(file_name,'w') as f:
            f.write(key)

        c.execute('update device_keys set issued=1 where id=?',(id_,))
        conn.commit()
        logging.info("Wrote private key #%d to %s", id_, file_name)
    except:
        logging.exception("Error while issuing key!")
        conn.rollback()
    finally:
        c.close()
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c= conn.cursor()
    # verify if the table already exists:
    c.execute("pragma table_info('device_keys')")
    if c.fetchone() is not None: return # table exists.

    try:
        c.executescript(
              '''create table device_keys (
                    id integer primary key,
                    public_key varchar(200) unique not null,
                    private_key varchar(2048) not null, 
                    issued bit default 0,
                    issued_to_mac varchar(20) default null,
                    issued_date float default null );''' )
        conn.commit()
    except:
        logging.exception( "Error creating key table: %s", DB_FILE )
        conn.rollback()
    finally:
        c.close()
        conn.close()


def signal_handler(signum,frame=None):
    logging.warn("SIGNAL %d; sending 'exit' event...", signum)
    exit.set()  # interrupt the key generator loop


def usage():
    print >>sys.stderr, "USAGE keygen.py  gen [count] | write [outfile.pem]"
    return 1


def main(args):
    if len(args) < 2: return usage()
    
    # install a signal handler to properly close the DB if 
    # the process is interrupted:
#    for s in ("SIGINT","SIGHUP","SIGTERM"):
#        signal.signal(getattr(signal,s),signal_handler)

    init_db()

    op = args[1]
    arg2 = args[2] if len(sys.argv) > 2 else None
    if op=='gen':
        if arg2: gen_keys(count=int(arg2))
        else: gen_keys()

    elif op=='write':
        if arg2: write_pem_file( arg2 )
        else: write_pem_file()

    else: return usage()
    return 0


logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stdout,
    format="%(asctime)s  %(message)s" )

if __name__ =='__main__': sys.exit( main(sys.argv) )
