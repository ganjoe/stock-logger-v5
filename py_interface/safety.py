from typing import List

def execute_panic_close(broker) -> bool:
    """
    F-INT-120: Immediately liquidates entire portfolio.
    """
    try:
        # Assuming broker has a bulk close method or we loop
        success = broker.close_all_positions()
        return success
    except Exception as e:
        print(f"Panic execution failed: {e}")
        return False
