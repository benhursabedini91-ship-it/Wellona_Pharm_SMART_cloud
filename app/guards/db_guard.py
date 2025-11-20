"""
DB Guard Helper - Kontrollon guard files para se të lejohet shkrim në DB.
"""
import os

GUARDS_DIR = os.path.dirname(__file__)
ALLOW_WRITE_FLAG = os.path.join(GUARDS_DIR, 'ALLOW_DB_WRITE.flag')
REQUIRE_CONFIRM_FLAG = os.path.join(GUARDS_DIR, 'REQUIRE_MANUAL_CONFIRM.flag')


class DBWriteBlocked(Exception):
    """Raised when DB write is attempted but guards block it."""
    pass


def check_db_write_allowed(operation_name: str = "DB write") -> bool:
    """
    Kontrollon nëse lejohet shkrim në DB.
    
    Logjika:
    1. Nëse ALLOW_DB_WRITE.flag mungon → ndalon (raise exception).
    2. Nëse REQUIRE_MANUAL_CONFIRM.flag ekziston → pyet përdoruesin në terminal.
    3. Nëse përdoruesi thotë JO → ndalon (raise exception).
    4. Përndryshe → lejon.
    
    Args:
        operation_name: Përshkrimi i operacionit (për mesazhin e konfirmimit).
    
    Returns:
        True nëse lejohet.
    
    Raises:
        DBWriteBlocked: Nëse guard file mungon ose përdoruesi refuzon.
    """
    # Check 1: ALLOW_DB_WRITE.flag must exist
    if not os.path.exists(ALLOW_WRITE_FLAG):
        raise DBWriteBlocked(
            f"DB write blocked: {ALLOW_WRITE_FLAG} nuk ekziston.\n"
            f"Për ta aktivizuar: type nul > {ALLOW_WRITE_FLAG}"
        )
    
    # Check 2: If REQUIRE_MANUAL_CONFIRM.flag exists, ask user
    if os.path.exists(REQUIRE_CONFIRM_FLAG):
        print(f"\n{'='*60}")
        print(f"KONFIRMIM I KËRKUAR: {operation_name}")
        print(f"{'='*60}")
        print(f"Operacioni kërkon të shkruajë në bazën e të dhënave.")
        print(f"Dëshiron ta vazhdosh? (shkruaj PO ose JO)")
        resp = input("Përgjigje: ").strip().upper()
        if resp not in ('PO', 'YES', 'Y'):
            raise DBWriteBlocked(f"Përdoruesi refuzoi: {operation_name}")
        print(f"Konfirmuar. Vazhdon...\n")
    
    return True


def is_db_write_enabled() -> bool:
    """
    Kthen True nëse ALLOW_DB_WRITE.flag ekziston (pa pyetur përdoruesin).
    Përdor këtë për të kontrolluar nëse duhet të inicializohet lidhja me DB.
    """
    return os.path.exists(ALLOW_WRITE_FLAG)


if __name__ == '__main__':
    # Test guard system
    print("Testing DB guard system...")
    try:
        check_db_write_allowed("Test DB Write")
        print("✓ DB write allowed.")
    except DBWriteBlocked as e:
        print(f"✗ Blocked: {e}")
