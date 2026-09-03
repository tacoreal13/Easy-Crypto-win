@echo off
@cd /d "%~dp0"

:: replace the wallet addresses with your own

:: mine to herominers
rigel.exe -a kawpow --coin quai -o stratum+tcp://de.quai.herominers.com:1185 -u YOUR_QUAI_WALLET -w my_rig --log-file logs/miner.log

:: mine to k1pool
::rigel.exe -a kawpow --coin quai -o stratum+tcp://eu.quai.k1pool.com:3333 -u YOUR_K1POOL_WALLET -w my_rig --log-file logs/miner.log

:: mine to kryptex
::rigel.exe -a kawpow --coin quai -o stratum+tcp://quai.kryptex.network:7777 -u YOUR_QUAI_WALLET -w my_rig --log-file logs/miner.log

pause
