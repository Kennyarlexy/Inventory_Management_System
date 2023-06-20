import cv2
import pandas as pd
import mysql.connector
from mysql.connector.cursor import MySQLCursor
from pyzbar.pyzbar import decode
import streamlit as st
import time

class BarcodeScanner:
    """
    BarcodeScanner memerlukan alamat ip kamera eksternal untuk dapat bekerja.
    BarcodeScanner ditujukan untuk dikonstruksi di main function agar tidak redundant
    """
    
    camera_ip = ""

    def __init__(self, camera_ip):
        self.camera_ip = camera_ip
    
    def read_barcode(self):
        """
        Fungsi ini membuka kamera smartphone (sesuai camera_ip), kemudian baca barcode hingga 10x dan cari frekuensi barcode yang paling banyak (mencegah kesalahan ketika scan/membaca barcode)

        return most_common_barcode: string
        """
        print("Sedang membaca barcode...")
        camera = cv2.VideoCapture()
        camera.open(self.camera_ip)

        while not camera.isOpened():
            st.warning("Camera not connected. Please make sure the camera is connected and try again.")
            camera.open(self.camera_ip)
            time.sleep(1)

        reading_cnt = 0
        barcode_frequency = {}
        while reading_cnt < 10:
            success, frame = camera.read()
            frame_h, frame_w, ignore = frame.shape
            frame = cv2.resize(frame, (frame_w // 2, frame_h // 2))
            cv2.namedWindow("Camera View")
            cv2.setWindowProperty("Camera View", cv2.WND_PROP_TOPMOST, 1)
            cv2.imshow("Camera View", frame)
            cv2.waitKey(1)
            
            barcodes = decode(frame)
            if len(barcodes) == 0:
                # print("no barcode detected")
                continue

            decoded_barcode = barcodes[0].data.decode("utf-8")
            reading_cnt += 1
            # print(f"decoded barcode: {decoded_barcode}")
            if decoded_barcode in barcode_frequency:
                barcode_frequency[decoded_barcode] += 1
            else:
                barcode_frequency[decoded_barcode] = 1
                
        camera.release()
        cv2.destroyAllWindows()
        
        most_common_barcode = max(barcode_frequency, key=barcode_frequency.get)
        return most_common_barcode

class Product:
    """
    class Product berisi informasi product.
    Informasi product dapat diambil dengan memanggil method get_data()
    """

    def __init__(self, barcode = "", name = "", stock = 0, price = 0.0):
        self.barcode = barcode
        self.name = name
        self.stock = stock
        self.price = price

    def get_data(self):
        return (self.barcode, self.name, self.stock, self.price)

class Inventory:
    def __init__(self, host, user, password, database):
        self.cnx = mysql.connector.connect(host=host, user=user, password=password, database=database)
        self.cursor = self.cnx.cursor()

        self.cursor.execute("CREATE DATABASE IF NOT EXISTS inventory_PBO_FEB;")
        self.cursor.execute("USE inventory_PBO_FEB;")

        query = """
            CREATE TABLE IF NOT EXISTS products (
                barcode varchar(25) NOT NULL,
                product_name varchar(25) NOT NULL,
                product_stock INT,
                product_price double,
                PRIMARY KEY (barcode)
            );
        """
        self.cursor.execute(query)

    def is_connected(self):
        return self.cnx.is_connected()

    def close_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.cnx.is_connected():
            self.cnx.close()

    def save_changes(self):
        self.cnx.commit()

    def count(self, barcode):
        query = "SELECT COUNT(*) FROM products WHERE barcode = %s;"
        self.cursor.execute(query, [barcode])
        count = self.cursor.fetchone()[0]

        return count
    
    def find(self, barcode):
        return self.count(barcode) > 0

    def add_product(self, product: Product): 
        query = """
            INSERT INTO products (barcode, product_name, product_stock, product_price)
            VALUES (%s, %s, %s, %s);
        """
        self.cursor.execute(query, product.get_data())

    def get_product(self, barcode):
        query = """
            SELECT *
            FROM products
            WHERE barcode = %s;
        """
        self.cursor.execute(query, [barcode])
        results = self.cursor.fetchall()
        product = Product(results[0], results[1], results[2], results[3])
        return product
    
    def get_product_info(self, barcode):
        query = """
            SELECT product_name, product_stock, product_price
            FROM products
            WHERE barcode = %s;
        """
        self.cursor.execute(query, [barcode])
        results = self.cursor.fetchall()
        return results[0]

    def update_product(self, barcode, new_name, new_stock, new_price):
        query = """
            UPDATE products
            SET product_name = %s, product_stock = %s, product_price = %s
            WHERE barcode = %s;
        """
        self.cursor.execute(query, [new_name, new_stock, new_price, barcode])

    def show_products(self):
        query = """
            SELECT *
            FROM products;
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        column_names = [desc[0] for desc in self.cursor.description]
        df = pd.DataFrame(results, columns=column_names)
        st.dataframe(df, use_container_width=True)

    def __delete_all_products(self):
        query = "DELETE FROM products"
        self.cursor.execute(query)
    
    def delete_product(self, barcode=None):
        if barcode is not None:
            query = """
                DELETE FROM products 
                WHERE barcode = %s;
            """
            self.cursor.execute(query, [barcode])
        else:
            self.__delete_all_products()
            print("all products cleared")

    
def main():
    st.set_page_config(
        page_title = "Inventory Management System",
        layout = "centered"
    )

    st.title("Sistem Manajemen Inventori")
    
    with st.sidebar:
        st.title("Koneksi Database MySQL")
        host_input = st.text_input("Host")
        user_input = st.text_input("User")
        password_input = st.text_input("Password", type="password")
        connect = st.button("Connect")

        if "connect_state" not in st.session_state:
            st.session_state["connect_state"] = False
        elif connect:
            st.session_state["connect_state"] = True
        else:
            connect = st.session_state["connect_state"]
        
        if connect:
            inventory = Inventory(
                host = host_input, 
                user = user_input, 
                password = password_input,
                database = "mysql"
            )
            
            if inventory.is_connected():
                st.write("Berhasil terkoneksi dengan database")
            else:
                st.write("Gagal terkoneksi dengan database")


    if "connect_state" not in st.session_state:
        st.session_state["connect_state"] = False
    elif connect:
        st.session_state["connect_state"] = True
    else:
        connect = st.session_state["connect_state"]
        
    if not connect:
        st.warning("""Harap hubungkan ke database MySQL terlebih dahulu!\n
        Langkah-langkah:

        1. Buka sidebar di sebelah kiri atas

        2. Isi host, misalnya localhost

        3. Isi user, misalnya root

        4. Isi password database

        5. Klik tombol Connect""")
        return

    camera_ip = st.text_input("IP-address kamera eksternal") # https://192.168.43.1:8080/video

    if not camera_ip:
        st.warning("""Harap memasukkan alamat IP kamera smartphone anda!\n
        Langkah-langkah:

        1. Download aplikasi "IP Webcam" di Google Playstore

        2. Pada aplikasi "IP Webcam", scroll ke bawah dan pilih Start Server

        3. Masukkan IP address yang tertera di layar, misalnya https://192.168.43.1:8080/video""")
        return

    barcode_scanner = BarcodeScanner(camera_ip)

    scan_barcode_btn = st.button("Mulai Scan")

    if scan_barcode_btn:
        st.session_state["scanned_barcode"] = ""
    elif "scanned_barcode" not in st.session_state:
        return
        
    barcode = st.session_state["scanned_barcode"]

    # jika barcode belum pernah discan
    if barcode == "":
        # dapatkan barcode dari barcode_scanner
        barcode = barcode_scanner.read_barcode()
        st.session_state["scanned_barcode"] = barcode
        if inventory.find(barcode):
            st.warning("barcode sudah terdata")

    st.write(f"Barcode: {barcode}")


    if not inventory.find(barcode):
        st.markdown("### Tambah Produk Baru")
        name_val = ""
        stock_val = 0
        price_val = 0
    else:
        st.markdown("### Update Produk Lama")
        name_val, stock_val, price_val = inventory.get_product_info(barcode)

    
    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        name = st.text_input("Nama Produk", value=name_val)
    with col_2:
        stock = st.number_input(
            label="Jumlah Stok",
            min_value=0,
            step=1,
            value=stock_val
        )
    with col_3:
        price = st.number_input(
            label="Harga Satuan",
            min_value=0,
            step=1000,
            value=int(price_val)
        )

    if not inventory.find(barcode):
        add = st.button("Tambah")

        if add:
            product = Product(barcode, name, stock, price)
            inventory.add_product(product)
            inventory.save_changes()
            st.session_state["scanned_barcode"] = ""
    else:
        update = st.button("Update")
        print("Entered")

        if update:
            inventory.update_product(barcode, name, stock, price)
            inventory.save_changes()
            st.session_state["scanned_barcode"] = ""

        
    st.markdown("### Daftar Produk Saat Ini")
    inventory.show_products()
    # inventory.delete_product()
        
    inventory.close_connection()

    print("proses selesai...")


if __name__ == "__main__":
    main()