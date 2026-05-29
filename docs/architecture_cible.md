# Architecture cible — Devastator

```mermaid
flowchart TB
    subgraph ALIMENTATION["Alimentation"]
        BATT_LOGIQUE["NiMH Tenergy PRO — pack maison"]
        SW_LOGIQUE["Interrupteur alimentation logique"]
        ALIM_LOGIQUE["Circuit d’alimentation 3,3 V / 5 V"]
        BUCK_3V3["Pololu 4090 D36V50F3"]
        BUCK_5V["Pololu 4091 D36V50F5"]
        VOLTM_LOGIQUE["Voltmètre logique"]

        BATT_MOTEUR["NiMH Melasta"]
        VOLTM_MOTEUR["Voltmètre moteurs"]
        INA260["Adafruit INA260"]
    end

    subgraph CALCUL["Calcul et contrôle"]
        RASPI4["Raspberry Pi 4 4 GB"]
        PICO_WH["Raspberry Pi Pico WH"]
    end

    subgraph TRACTION["Traction"]
        MDD3A["Cytron MDD3A"]
        FIT0521_G["DFRobot FIT0521 gauche"]
        FIT0521_D["DFRobot FIT0521 droit"]
    end

    subgraph SONAR["Détection obstacle simple"]
        SERVO_TOUR["Hitec HS-422"]
        ULTRASON["Grove Ultrasonic Ranger"]
    end

    subgraph INTERFACES["Interface opérateur et retours"]
        PS2["Manette Lynxmotion PS2"]
        AUDIO_I2S["MAX98357 + PCM5102A"]
        HP_BF37["Visaton BF 37"]
        LCD2["Waveshare LCD 2 pouces ST7789V"]
        MIC_ARRAY["ReSpeaker Mic Array v3.0"]
    end

    subgraph PERCEPTION["Perception avancée"]
        RPLIDAR["Slamtec RPLIDAR A1M8"]
        REALSENSE["Intel RealSense D435IF"]
    end

    BATT_LOGIQUE --> SW_LOGIQUE
    SW_LOGIQUE --> ALIM_LOGIQUE
    ALIM_LOGIQUE --> BUCK_3V3
    ALIM_LOGIQUE --> BUCK_5V
    BATT_LOGIQUE --> VOLTM_LOGIQUE

    BUCK_5V --> RASPI4
    BUCK_5V --> PICO_WH
    BUCK_5V --> SERVO_TOUR
    BUCK_3V3 --> ULTRASON

    BATT_MOTEUR --> VOLTM_MOTEUR
    BATT_MOTEUR --> MDD3A

    RASPI4 --> PICO_WH
    PICO_WH --> MDD3A
    MDD3A --> FIT0521_G
    MDD3A --> FIT0521_D

    PICO_WH --> SERVO_TOUR
    SERVO_TOUR --> ULTRASON
    ULTRASON --> PICO_WH
    PICO_WH --> RASPI4

    PS2 --> RASPI4
    RASPI4 --> AUDIO_I2S
    AUDIO_I2S --> HP_BF37
    RASPI4 --> LCD2
    MIC_ARRAY --> RASPI4

    RPLIDAR --> RASPI4
    REALSENSE --> RASPI4

    INA260 -.-> ALIM_LOGIQUE
    INA260 -.-> RASPI4

    classDef actif fill:#d8f5d0,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef gele fill:#fff3cd,stroke:#b8860b,stroke-width:2px,color:#000
    classDef futur fill:#e2e3e5,stroke:#6c757d,stroke-width:2px,color:#000

    class RASPI4,PICO_WH,MDD3A,FIT0521_G,FIT0521_D,ULTRASON,SERVO_TOUR actif
    class BATT_LOGIQUE,BATT_MOTEUR,VOLTM_LOGIQUE,VOLTM_MOTEUR actif
    class BUCK_3V3,BUCK_5V,ALIM_LOGIQUE,SW_LOGIQUE actif

    class PS2,AUDIO_I2S,HP_BF37,RPLIDAR gele

    class INA260,REALSENSE,LCD2,MIC_ARRAY futur