"""Invented names, addresses and non-routable 000-prefixed demonstration phones."""
DEMO = [
    dict(full_name="Aarav Demo", dob="2001-05-12", phone="0000000101", address="14 Example Lane, Demo Nagar"),
    dict(full_name="Aarav Demo", dob="2001-05-12", phone="0000000101", address="14 Example Lane, Demo Nagar"),
    dict(full_name="Mira Sample", dob="1998-09-03", phone="0000000102", address="22 Fiction Road, Sample Town"),
    dict(full_name="Meera Sample", dob="1998-09-03", phone="0000000102", address="22 Fiction Rd, Sample Town"),
    dict(full_name="Kavin Test", dob="2002-11-20", phone="0000000103", address="8 Imaginary Street, Demo Nagar"),
    dict(full_name="Kavin Tset", dob="2002-11-20", phone="0000000103", address="8 Imaginary St, Demo Nagar"),
    dict(full_name="Nila Example", dob="1995-02-17", phone="0000000104", address="3 Mock Avenue, Sample Town"),
    dict(full_name="Rohan Fiction", dob="1989-07-06", phone="0000000105", address="91 Practice Road, Demo Nagar"),
]

for _index, _record in enumerate(DEMO, 1):
    _record["aadhaar_ref"] = f"DEMO-AAD-{_index:04d}"
    _record["licence_ref"] = f"DEMO-DL-{_index:04d}"
