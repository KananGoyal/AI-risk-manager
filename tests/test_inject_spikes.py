import pytest
import pandas as pd
from src.person_a.clean_data import generate_synthetic_sparkov_base
from src.person_a.inject_fraud_spikes import (
    inject_card_testing,
    inject_account_takeover,
    inject_velocity_abuse,
)

def test_inject_spikes_determinism():
    base_df = generate_synthetic_sparkov_base(n_samples=200, seed=42)
    
    injected_1 = inject_card_testing(base_df.copy(), seed=100)
    injected_2 = inject_card_testing(base_df.copy(), seed=100)
    
    assert len(injected_1) == len(injected_2)
    pd.testing.assert_frame_equal(injected_1, injected_2)

def test_inject_spikes_fraud_labels():
    base_df = generate_synthetic_sparkov_base(n_samples=200, seed=42)
    
    injected = inject_account_takeover(base_df.copy(), n_bursts=5, seed=101)
    new_rows = injected[injected["spike_type"] == "account_takeover"]
    
    assert len(new_rows) == 5
    assert (new_rows["is_fraud"] == 1).all()
