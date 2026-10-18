from app.security.password_hashing import hash_password, verify_password
def test_password_hash():
    hashed=hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password(hashed,"correct horse battery")
    assert not verify_password(hashed,"wrong password")
