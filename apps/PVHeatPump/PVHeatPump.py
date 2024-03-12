##############################################################################################
# PVHeatPump
# Author: Gerard Mamelle (2024)
# Version : 1.0.1
# Program under MIT licence
##############################################################################################
import hassapi as hass
import math
import datetime
from datetime import timedelta

OUTSIDE_THRESHOLD_TEMPERATURE = 15.0
COMFORT_THRESHOLD_TEMPERATURE = 20.5
REDUCED_THRESHOLD_TEMPERATURE = 19.5
FORCED_MAX_DURATION = 3

class PVHeatPump(hass.Hass):

    def initialize(self):
        self.start_inside_threshold_temperature = self.get_safe_float("threshold_temperature")
        self.comfort_heating = self.get_state(self.args["comfort_heating"])
        self.tomorrow_morning_temperature = self.get_safe_float("tomorrow_morning_temperature")
        #self.tomorrow_solar_energy_forecast = self.get_safe_float("tomorrow_solar_energy_forecast ")
        self.off_peak = self.get_state(self.args["off_peak"])
        self.grid_power_online = self.get_state(self.args["grid_power_online"])
        self.start_heat_pump = 'off'
        self.set_state(self.args["start_heat_pump"],state='off')
        # forced mode = mode 2 (end night start)
        duree = self.get_safe_float("forced_mode_max_duration")
        if duree != None:
            self.forced_max_duration = int(duree)
        else:
            self.forced_max_duration = FORCED_MAX_DURATION
        self.forced_mode = self.get_state(self.args["forced_mode"])
        self.forced_mode_start_time = self.datetime() + timedelta(hours=24)
        self.timer = None
        
        # Init listen for pool events
        self.listen_state(self.change_inside_temperature,self.args["inside_temperature"])
        self.listen_state(self.change_outside_temperature,self.args["outside_temperature"])
        self.listen_state(self.change_off_peak,self.args["off_peak"])
        self.listen_state(self.change_comfort_heating,self.args["comfort_heating"])
        self.listen_state(self.change_tempo_color,self.args["current_tempo_color"])                   
        self.listen_state(self.change_forced_mode,self.args["forced_mode"])                   
        self.listen_state(self.change_forced_mode_duration,self.args["forced_mode_max_duration"])   
        self.listen_state(self.change_threshold_temperature,self.args["threshold_temperature"])          
        if self.args["enable_solar_optimizer"] == "":
            self.enable_solar_optimizer = "off"
        else:
            self.enable_solar_optimizer = self.get_state(self.args["enable_solar_optimizer"])
            self.listen_state(self.change_enable_solaroptimizer,self.args["enable_solar_optimizer"])  
            self.listen_state(self.change_start_heating,self.args["start_heat_pump"])                          
        if self.args["grid_power_online"] != "":
            self.listen_state(self.change_grid_power_online,self.args["grid_power_online"])
        
        self.run_daily(self.check_forced_mode, "01:00:00")
        self.run_daily(self.optimize_heating, "21:30:00")

        #set tempo day
        self.current_tempo_color = self.get_state(self.args["current_tempo_color"])
        self.tomorrow_tempo_color = self.get_state(self.args["tomorrow_tempo_color"])
        # Set temperature de reference
        self.set_temperature_reference()
        # Try to turn on HP
        self.check_HP()
        # Initialisation terminee 
        self.log('PVHeatPump initialized')
    
    @property
    def inside_temperature(self) -> float:
        try:
            return float(self.get_safe_float("inside_temperature"))
        except Exception as e:
            self.log("Error getting inside temperature", e)
            return None

    @property
    def outside_temperature(self) -> float:
        try:
            return float(self.get_safe_float("outside_temperature"))
        except Exception as e:
            self.log("Error getting outside temperature", e)
            return None

    def get_safe_float(self, entity_id: str):
        state = self.get_state(self.args[entity_id])
        if not state or state == "unknown" or state == "unavailable":
            return None
        float_val = float(state)
        return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val

    # Change tempo color
    def change_tempo_color(self, entity, attribute, old_state, new_state, kwargs):
        self.log(f'Day tempo color = {new_state}')
        self.current_tempo_color = new_state
        self.check_HP()

    # Change off peak 
    def change_off_peak(self, entity, attribute, old_state, new_state, kwargs):
        self.log(f'Off peak = {new_state}')
        self.off_peak = new_state
        self.check_HP()
    
    # Change optimizer status
    def change_enable_solaroptimizer(self, entity, attribute, old_state, new_state, kwargs):
        self.log(f'Solar optimizer = {new_state}')
        self.enable_solar_optimizer = new_state
        self.check_HP()
    
    # Change start status from optimizer
    def change_start_heating(self, entity, attribute, old_state, new_state, kwargs):
        self.log(f'Start HP = {new_state}')
        self.start_heat_pump = new_state 
        self.check_HP()
     
    # Power failure, we stop heat pump
    def change_grid_power_online(self, entity, attribute, old_state, new_state, kwargs):
        if new_state == 'Online' :
            self.grid_power_online = 'Online'
            self.check_HP()            
            self.log("Grid power on")
        else:
            if new_state == 'On Battery' :
                self.grid_power_online = 'On Battery'
                self.turn_off(self.args['heat_pump_command'])
                self.log("Power failure, heat pump off")
    
    def change_forced_mode_duration(self, entity, attribute, old_state, new_state, kwargs):
        forced_mode_duration= self.get_safe_float("forced_mode_max_duration")
        if forced_mode_duration!= None:
            self.forced_max_duration = int(forced_mode_duration)
         
    def change_forced_mode(self, entity, attribute, old_state, new_state, kwargs):
        self.forced_mode = new_state
        self.check_forced_mode(None)
    
    def change_threshold_temperature(self, entity, attribute, old_state, new_state, kwargs):
        self.start_inside_threshold_temperature = self.get_safe_float("threshold_temperature")
        self.check_HP()

    # definition de la temperature de declenchement de la HP en fonction de la comfort_heating
    def set_temperature_reference(self):
        if self.comfort_heating == 'on':
            self.start_inside_threshold_temperature = COMFORT_THRESHOLD_TEMPERATURE
        else:
            self.start_inside_threshold_temperature = REDUCED_THRESHOLD_TEMPERATURE
        self.log(f'Temperature de declenchement = {self.start_inside_threshold_temperature}')

    def change_inside_temperature(self, entity, attribute, old_state, new_state, kwargs):
        if self.inside_temperature == None:
            return
        self.check_HP()
    
    def change_outside_temperature(self, entity, attribute, old_state, new_state, kwargs):
        if self.outside_temperature == None:
            return
        self.check_HP()

    def change_comfort_heating(self, entity, attribute, old_state, new_state, kwargs):
        self.comfort_heating = new_state
        self.set_temperature_reference()
        self.log(f'comfort_heating = {self.comfort_heating}')
        self.check_HP()

    def do_check_HP(self,kwargs):
        self.check_HP()

    # Mise en route marche forcee 
    def check_forced_mode(self,kwargs):
        if self.timer != None: 
            self.cancel_timer(self.timer)
        if self.forced_mode == 'off':
            self.forced_mode_start_time = self.datetime() + timedelta(hours = 24)
        else:
            delai = 5 - self.forced_max_duration
            self.forced_mode_start_time = self.datetime() + timedelta(hours = delai)
            self.log(f'start time = {self.forced_mode_start_time}')
            self.timer = self.run_at(self.do_check_HP, self.forced_mode_start_time)
            self.check_HP()
    
    # Optimisation de la duree de fonctionnement de la HP
    def optimize_heating(self, kwargs):
        self.tomorrow_morning_temperature = self.get_safe_float("tomorrow_morning_temperature")
        # if self.args['tomorrow_solar_energy_forecast'] != "":
        #    self.tomorrow_solar_energy_forecast = self.get_safe_float("tomorrow_solar_energy_forecast")
        self.tomorrow_tempo_color = self.get_state(self.args["tomorrow_tempo_color"])
        # Conditions et duree de mise en route marche forcee
        if (self.inside_temperature > (self.start_inside_threshold_temperature - 1.0)
            and self.tomorrow_morning_temperature > 5.0
            and self.tomorrow_tempo_color != "Rouge"):
            self.forced_mode = 'on'
            if self.tomorrow_morning_temperature < 0.0:
                self.forced_max_duration = 5
            elif self.tomorrow_morning_temperature < 7.0:
                self.forced_max_duration = 4
            elif self.tomorrow_morning_temperature < 10.0:
                self.forced_max_duration = 3
            else:
                self.forced_max_duration = 2
            # si la journée du lendemain est ensoleillee on prévoit de chauffer dans la journée
            # if self.tomorrow_solar_energy_forecast > 15.0:
            #    self.forced_max_duration = self.forced_max_duration - 1            
            self.set_state(self.args['forced_mode_max_duration'], state = float(self.forced_max_duration))
            self.set_state(self.args['forced_mode'], state = 'on')
        else:
            self.forced_mode = 'off'
            self.set_state(self.args['forced_mode'], state = 'off')
        self.log(f'Forced mode = {self.forced_mode}')


    # Heat pump regulation function
    def check_HP(self):
        try:
            status_HP = self.get_state(self.args["heat_pump_command"])
        except KeyError:
            self.log(f'Could not get status HP : {status_HP}')
            return
        if self.inside_temperature == None or self.outside_temperature == None:
            return

        # mode 2 Regulation
        if self.forced_mode == 'on':
            if self.off_peak == 'off':
                if status_HP == "on":
                    self.turn_off(self.args['heat_pump_command'])
                    self.log("Stop HP, Off peak off")
                    self.set_state(self.args['forced_mode'], state = 'off')
                    self.forced_mode_start_time = self.datetime() + timedelta(hours = 24)
                return
           # Mise en route mode 2 de la HP 
            if self.forced_mode_start_time < self.datetime():
                if status_HP == "off":
                    self.turn_on_HP()                    
                    self.log("Start HP")
            return     

        # Night Regulation mode 1
        if self.off_peak == 'on':
            if (self.inside_temperature <= self.start_inside_threshold_temperature 
                and self.outside_temperature < OUTSIDE_THRESHOLD_TEMPERATURE):
                if status_HP == "off":
                    self.turn_on_HP()
                    self.log("Night Auto start HP")
                    return
            if status_HP == "on" and self.inside_temperature > self.start_inside_threshold_temperature:
                self.turn_off(self.args['heat_pump_command'])
                self.log("Night auto stop HP")
            return

        # Day Regulation PVOptimizer
        if self.enable_solar_optimizer == 'on':
            # start HP if start command is on
            if self.start_heat_pump == 'on':
                if self.inside_temperature < self.start_inside_threshold_temperature :
                    if status_HP == "off" and not self.current_tempo_color == 'Rouge' :
                        self.turn_on_HP()                   
                        self.log("Start HP (PVOptimizer)")
                        return
            # stop HP if start command is off
            else: 
                if status_HP == "on":
                    self.turn_off(self.args['heat_pump_command'])
                    self.log("Stop HP (PVOptimizer)")
                    return
            # set required pvoptimizer status on if inside temp is low, better to do manually
            #if status_HP == "off" and self.inside_temperature < self.start_inside_threshold_temperature and self.current_tempo_color == "Bleu":
            #    self.set_state(self.args['heat_pump_query'], state = 'on')
            #    self.log ('Query HP on')
            #    return

            # stop HP if inside temp is high
            if status_HP == "on" and self.inside_temperature > self.start_inside_threshold_temperature :
                self.set_state(self.args['heat_pump_query'], state = 'off')
                self.turn_off(self.args['heat_pump_command'])
                self.log ('Stop HP')
        
    # Start HP and Check if HP is running well
    def turn_on_HP(self):
        self.turn_on(self.args['heat_pump_command'])
        if self.args['heat_pump_water_temperature'] != "":
            self.run_in(self.check_temperature, 30*60)

    def start_heating(self, kwargs):
        self.turn_on_HP()

    # Check if HP water temperature is increasing and notify if not
    def check_temperature(self, kwargs):
        temperature = self.get_safe_float("heat_pump_water_temperature")
        if temperature == None:
            return
        if temperature < 24.0:
            self.call_service("notify/telegram_maison",message="HP not running well")
            self.log("HP not running well")

    def getdifference_minutes(self,recent, old):
        diff = recent - old
        minutes = diff.total_seconds() / 60
        return int(minutes)
    
