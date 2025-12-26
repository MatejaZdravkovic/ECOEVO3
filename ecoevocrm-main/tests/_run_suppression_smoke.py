from ecoevocrm.suppression_config import get_suppression_params
p = get_suppression_params(quick_test=False)
print('OK', p['influx_values'].shape, len(p['influx_times']), p['num_resources'])
