# PVHeatPump
Cette application Appdaemon pour Home Assistant permet de réguler les pompes à chaleur air-eau et plus particulièrement celles qui utilisent un plancher chauffant. On peut aussi l’utiliser avec des circuits de chauffage central. 

Ce mode de chauffage par PAC a pour particularité d’avoir une forte inertie qui lui confère à la fois des avantages tels que la mise en route du chauffage de nuit en heures creuses pour se chauffer le jour ce qui permet de faire des économies mais aussi des inconvénients en termes de régulation car il faut anticiper la chauffe et de montée en température qui se fait lentement sur plusieurs heures. 

Les PAC ont une régulation interne, prenant en compte la température intérieure et la température extérieure pour assurer la régulation de la température en suivant la courbe d’eau. Elles fonctionnement souvent avec une horloge de fonctionnement et une sonde thermostatique intérieure.

Ce logiciel vient remplacer le thermostat intérieur qui travaille sur un switch dans la PAC. Il permet d’optimiser la dépense énergétique en fonctionnant en heures creuses et si besoin, dans la journée au moment où la production solaire le permet. 
Pour cela il est couplé à l’application **[PVOptimizer](https://github.com/loudemer/pvoptimizer)** qui distribue l’énergie solaire à tous les gros consommateurs de la maison.

Il est possible de faire fonctionner cette application de manière autonome sans PVOptimizer. Le mode de fonctionnement 3 décrit ci-dessous n’est alors pas disponible
# Fonctionnement
L’application utilise trois modes de fonctionnement qui peuvent se compléter :

1. Un fonctionnement nocturne classique pendant les heures creuses. Le logiciel s’occupe alors de mettre en route la PAC en heures creuses lorsque les températures intérieures et extérieure deviennent basses. 
   Il s’occupe aussi d’arrêter la PAC lorsque la température de consigne intérieure est atteinte ou lorsque l’on bascule en heures pleines
1. Un fonctionnement nocturne limité (marche forcée) qui concerne les périodes où les températures extérieures ne sont pas trop basses ne nécessitant alors pas un chauffage toute la nuit. 
Le logiciel met en route la PAC, une ou plusieurs heures en fin de nuit avant la bascule en heures pleines ce qui permet de chauffer la maison de manière optimale en gardant un maximum d’énergie pour la journée. Ce mode de fonctionnement est alternatif au premier. 
   Pour calculer le nombre d’heures de chauffe nécessaires, le logiciel prend en compte les températures extérieures et intérieures, ainsi que la prévision de température le lendemain matin. Il est prévu de prendre en compte la prévision de production solaire mais celle ci est pour l'instant peu fiable.
1. Un fonctionnement diurne que l’on qualifiera de complémentaire dans les périodes de grand froid qui va se faire en plus du fonctionnement nocturne au moment où la production d’énergie solaire est maximale. Ce troisième mode est piloté par l’application : PVOptimizer. 
   La demande de mise en route peut se fait sur le dasboard de PVOptimizer sinon elle se fait automatiquement à partir de l'application lorsque la température demandé n'est pas atteinte.

Le choix entre les modes 1 et 2 est effectuée par le logiciel en fonction des températures intérieures et extérieures le soir à 21h30.
On peut sélectionner soi-même le mode 1 ou 2 si besoin.

# Prérequis
- Installation de appdaemon
- Installation de PVOptimiseur
- Sensor relai PAC (en remplacement du contacteur du thermostat d’ambiance)
- Couleur du jour pour les abonnements tempo 
On peut utiliser l’**[API RTE](https://www.api-couleur-tempo.fr/api)**
- Sensor Heures Creuses
Disponible dans l’API RTE
- Prévision de la température du lendemain
- Sensor température intérieure 
(A placer dans une pièce éloignée de la cheminée s’il y en a une)
- Sensor de consigne confort ou réduit (absence prolongée)
- Sensor température de consigne
# Installation
1. Installer **l’add-on appdaemon** à partir de paramètres / modules complémentaires si cela n’est pas déjà fait.
1. **[Télécharger le dépôt](https://github.com/loudemer/PVHeatPump.git)**
1. Mettre les fichiers *PVHeatPump.py et PVHeatPump.yaml* dans le répertoire *addon\_configs/a0d7b954\_appdaemon/apps*
1. Mettre le fichier *optimizerentities.yaml* dans le répertoire */config/* de HA ou dans un sous répertoire dédié au fichiers yaml si vous en avez un.
# Configuration
1. Ajouter dans le fichier `addon_configs/a0d7b954_appdaemon/appdaemon.yaml`
```   
      pvheatpump_log :
        name: PVHeatPumpLog
        filename: /homeassistant/log/pvheatpump.log
        log_generations: 3
        log_size: 100000
```
   Ceci vous permet de lire les log de l’application dans le fichier /config/ pvheatpump\_log  ou directement dans http://ip\_ha:5050
1. **Compléter** le fichier `/addon_configs/a0d7b954_appdaemon/apps/PVHeatPump.yaml` :

Certains sensors sont optionnels : `heat_pump_water_temperature`, `grid_power_online`.

Si vous n'utilisez pas PVOptimizer les sensors `enable_solar_optimizer`, `start_heat_pump`sont aussi optionnels
Il faut alors mettre un sensor vide : "" à la place.

Pour les autres, il faut créer les sensors qui ne sont pas déjà présents dans votre configuration.
```
PVHeatPump:
  class: PVHeatPump
  module: PVHeatPump
  log: pvheatpump_log
  # Arret / Marche de l'application PAC
  constrain_input_boolean: input_boolean.enable_heating

  # temperature interieure
  inside_temperature: sensor.temperature_cellier
  # temperature exterieure
  outside_temperature: sensor.temperature_toit
  # temperature demandee
  threshold_temperature: input_number.chauffage_demande
  # mode confort ou reduit (absence)
  comfort_heating: input_boolean.chauffage_confort

  # switch commande PAC
  heat_pump_command: switch.relai_pac
  # temperature circuit eau PAC (optionnel)
  heat_pump_water_temperature: sensor.temperature_pac

  # Couleur tempo du jour
  current_tempo_color: sensor.rte_tempo_couleur_actuelle
  # Couleur tempo du lendemain
  tomorrow_tempo_color: sensor.rte_tempo_prochaine_couleur
  # indicateur HP / HC
  off_peak: binary_sensor.rte_tempo_heures_creuses

  # Marche forcee (mode 2) 
  forced_mode: input_boolean.marche_forcee_pac
  # Duree marche forcee
  forced_mode_max_duration: input_number.duree_max_marche_forcee_pac
  # Prevision temperature lendemain matin
  tomorrow_morning_temperature: sensor.temperature_forecast_next_day

  # Prevision ensoleillement lendemain 
  # tomorrow_solar_energy_forecast : sensor.energy_production_tomorrow
  # Indicateur coupure de courant (onduleur) (Optionnel)
  grid_power_online: sensor.ups_status

  # Mise en route de la PAC par PVOptimizer : input_boolean.start_device_x
  # (x etant le rang de l'appareil dans la liste commencant par 1)
  # (optionnel)
  start_heat_pump: input_boolean.start_device_4
  start_heat_pump: input_boolean.start_device_4
  # Demande de mise en route de la PAC a PVOptimizer (optionnel)
  heat_pump_query: input_boolean.device_request_4
  # Application PVOptimizer disponible (optionnel)
  enable_solar_optimizer: input_boolean.enable_solar_optimizer

```

# Le Dashboard
A titre d’exemple vous trouverez dans le dépôt un fichier yaml d’exemple de configuration de base tout à fait perfectible.
> ![Icon](https://github.com/loudemer/pvheatpump/blob/main/images/dashboard.png?raw=true)
```
type: vertical-stack
title: PAC
cards:
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: switch.relai_pac
        tap_action:
          action: more-info
        hold_action:
          action: toggle
        icon_color: yellow
        layout: vertical
        name: Activation
        primary_info: name
        secondary_info: state
      - type: custom:mushroom-entity-card
        entity: input_boolean.marche_forcee_pac
        icon_color: yellow
        layout: vertical
        tap_action:
          action: toggle
        hold_action:
          action: more-info
        name: Marche forcée
        primary_info: name
        secondary_info: state
      - type: custom:mushroom-entity-card
        entity: sensor.temperature_pac
        layout: vertical
        name: Temp eau PAC
        primary_info: name
        tap_action:
          action: more-info
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-number-card
        entity: input_number.duree_max_marche_forcee_pac
        name: Durée M. forcée
        icon: mdi:battery-clock-outline
        icon_color: yellow
        display_mode: buttons
      - type: custom:mushroom-number-card
        entity: input_number.chauffage_demande
        name: Temp demandée
        icon_color: accent
        icon: mdi:temperature-celsius
        primary_info: name
        display_mode: buttons
        tap_action:
          action: more-info

```

# Mode d’emploi
Une fois l’installation réalisée, l’intégration est opérationnelle.
Vous devez déterminer votre température seuil `threshold_temperature`,
Chaque soir, vous pouvez intervenir sur le mode de fonctionnement nocturne (mode 1 ou 2) si celui qui a été choisi ne vous convient pas.

## Visualisation des problèmes
L’intégration génère un fichier de log qui est stocké dans le fichier `/config/log/pvheatpump.log`.
Il est possible aussi d’avoir plus de détails en appelant directement la **[console de debug d’appdaemon](http://<ip_homeassistant>:5050)**

Vous pourrez alors voir le démarrage et l’arrêt de l’intégration dans *main_log*, les erreurs éventuelles dans *error_log* et le déroulement de l’activité de l’intégration dans *pvheatpump_log*.
# Désinstallation
Il faut retirer les 2 fichiers *PVHeatPump.py et PVHeatPump.py.yaml* dans le répertoire *addon\_configs/a0d7b954\_appdaemon/apps/*
Retirer aussi le dashboard PVHeatPump
Redémarrer HA.

