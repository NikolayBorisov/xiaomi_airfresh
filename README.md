# xiaomi_airfresh
Add support Xiaomi Mi Air Purifier A1 (MJXFJ-150-A1)
Model: dmaker.airfresh.a1

### HACS

Can be installed via [HACS](https://hacs.xyz/ Home Assistant Community Store).

Just add this [repository](https://github.com/NikolayBorisov/xiaomi_airfresh).

### Support

Availiable Attributes:
* power
* pm25
* co2
* temperature_outside
* favourite_speed
* filter_rate
* filter_day
* control_speed
* ptc_on
* ptc_status
* child_lock
* sound
* display
* mode

Availiable Services:
* airfresh_set_ptc_on / airfresh_set_ptc_off
* airfresh_set_sound_on / airfresh_set_sound_off
* airfresh_set_display_on / airfresh_set_display_off
* airfresh_set_filter_reset
* airfresh_set_favourite_speed (speed: 1-200)

### Configuration:

```yaml
fan:
  - platform: xiaomi_airfresh
    host: 192.168.1.44
    token: "cbnflp9iacbs2d9ho6p3d9z7ghrebqpo"
    name: Air Fresh
    model: dmaker.airfresh.a1
```
