# TagPulse Changelog
Sun 26/10/2025 12:31 - v0.4.61 (stable) FIX: Inventory sync now sends all available machine fields to Supabase including hostname windows_product_id total_ram_gb disk_type and CPU performance metrics

Sun 26/10/2025 12:18 - v0.4.60 (stable) CRITICAL FIX: Database path backslashes properly escaped. v0.4.59 had malformed path preventing DB check. This version REALLY works

Sun 26/10/2025 12:10 - v0.4.59 (stable) MAJOR SIMPLIFICATION: Desktop app now checks database directly instead of registry. Eliminates race conditions and sync issues. Single source of truth

Sun 26/10/2025 11:55 - v0.4.58 (stable) CLEANUP: Complete removal of all console mode code. Deleted console_display files removed 369 lines from main.cpp cleaned all console references from codebase.

Sun 26/10/2025 11:38 - v0.4.57 (stable) REAL FIX: Registry key now properly set in SERVICE MODE startup path. Previous v0.4.56 only had fix in console mode. This version fixes identity redirect issue for ALL remote machines.

Sun 26/10/2025 11:12 - v0.4.56 (stable) CRITICAL FIX: Set registry key at service startup when identity exists in database. Fixes issue where desktop app opens /first-run even when identity is already initialized.

Sun 26/10/2025 10:52 - v0.4.55 (stable) CRITICAL FIX: CHE now loads historical learning data properly. Restores millions of samples that were not being loaded after WAL refactoring. Uses DbOperationsHandler for thread-safe database access.

Sun 26/10/2025 10:42 - v0.4.54 (stable) CRITICAL FIX: Identity check logic bug. Fixed need_identity default value - must assume identity needed unless proven otherwise. This fixes the infinite first-run redirect loop when database queries fail.

Sun 26/10/2025 10:10 - v0.4.53 (stable) CRITICAL FIX: Database column name bug causing first-run redirect loop. Fixed perf_custom_* column names in SaveToDatabase. This fixes remote machine identity issues after fresh start.

Sun 26/10/2025 09:28 - v0.4.52 (stable) CRITICAL FIX: CHE API crashes from std::stoi empty string errors. All 6 CHE components now handle NULL values from ExecuteSelectQuery. FIX: Race condition - periodic syncs skip identity fields to prevent overwriting two-star commands. CHANGED: Remote command check now runs every 30 minutes.

Sun 26/10/2025 08:31 - v0.4.51 (stable) FEATURE: Two-star command system for remote field updates. Prefix company_name or user_full_name with ** in Supabase to update local machines on startup.

Sun 26/10/2025 08:05 - v0.4.50 (stable) ADDED: disk_primary_type field now syncs to Supabase machines table. Shows NVME SSD or HDD from primary disk.

Sun 26/10/2025 07:41 - v0.4.49 (stable) ADDED: Automatic cleanup of contaminated CHE temperature baselines during housekeeping. Removes baselines with unrealistic temps below 15C from LHM sensor failures.

Sun 26/10/2025 07:32 - v0.4.48 (stable) PROPERLY FIXED: Database WAL growth - all 5 CHE Load functions now use ExecuteSelectQuery instead of direct SQLiteManager access. This prevents read locks that were blocking WAL checkpoints.

Sun 26/10/2025 07:14 - v0.4.47 (stable) FIX: CHE temperature baseline validation - prevent zero/invalid temperatures from LHM failures from contaminating baselines. Minimum 15C threshold added.

Sun 26/10/2025 07:00 - v0.4.46 (stable) FIX: Missing performance fields in Supabase sync. Added perf_cpu_logical_cores perf_cpu_max_ghz perf_classification_reason perf_benchmark_ms. Removed jsoncpp from component_versions.

Sun 26/10/2025 06:51 - v0.4.45 (stable) CRITICAL FIX: WAL growth issue - Fixed 10 CHE files violating database access policy causing database locks that prevented WAL checkpoints

Sat 25/10/2025 20:56 - v0.4.43 (stable) CRITICAL FIX: Removed excessive UpdateLastSeen calls from cloud exporter - was being called on every export causing 1MB WAL growth per minute

Sat 25/10/2025 20:49 - v0.4.42 (stable) CRITICAL FIX: WAL checkpoint deadlock - removed manual transactions that were preventing database checkpoints from running causing WAL to grow to 40MB+

Sat 25/10/2025 19:49 - v0.4.41 (stable) TEST: Verifying automatic background scheduler continues working after v0.4.40 fix. This update should be picked up automatically within 2-4 minutes.

Sat 25/10/2025 19:44 - v0.4.40 (stable) CRITICAL FIX: Scheduler thread now starts even when updater is already running. This fixes automatic background updates failing after service restart during an update.

Sat 25/10/2025 19:36 - v0.4.39 (stable) TEST: Verifying automatic background update scheduler picks up updates within 15 minutes

Sat 25/10/2025 19:13 - v0.4.38 (stable) FIX: PawnIO driver installation moved to StartServices - the correct entry point for Windows service mode. v0.4.37 only ran in main which is bypassed when service starts.

Sat 25/10/2025 19:02 - v0.4.37 (stable) FIX: Automatic PawnIO driver installation on service startup. Ensures hardware sensors work without manual driver installation.

Sat 25/10/2025 18:45 - v0.4.36 (stable) FIX: Rebuild LHM service with properly bundled .NET runtime to fix sensor data extraction

Sat 25/10/2025 18:15 - v0.4.35 (stable) ROOT CAUSE FIX: LoadFromFile now validates neuron IDs exist before adding to layers. This prevents orphaned neuron IDs from causing null pointer crashes. Logs show any file corruption detected.

Sat 25/10/2025 18:09 - v0.4.34 (stable) CRITICAL FIX: Null pointer crash in evolving neural network Train function. Added safety checks when accessing neurons during backpropagation weight updates.

Sat 25/10/2025 17:56 - v0.4.33 (stable) CRITICAL FIX: Null pointer crash in evolving neural network Forward function. Added safety checks when accessing neurons from map to prevent crash 5 seconds after startup. Re-enabled fleet learning.

Sat 25/10/2025 17:37 - v0.4.32 (stable) CRASH FIX: Temporarily disabled fleet learning to diagnose crash occurring 5 seconds after startup. Also fixed neural migration version detection bug.

Sat 25/10/2025 17:31 - v0.4.31 (stable) FIX: Neural migration version detection bug - read int instead of size_t to correctly identify network file versions. Fixes spurious Unrecognized network file header warnings.

Sat 25/10/2025 17:11 - v0.4.30 (stable) CRITICAL FIX: Database schema column names corrected from custom_* to perf_custom_* matching code expectations. This fixes perf_custom_* fields failing to sync to Supabase.

Sat 25/10/2025 15:56 - v0.4.29 (stable) FIX: Performance fields now sync to Supabase. ingest-rollup now updates all perf_* fields including benchmark_ms classification_reason cpu cores/ghz etc.

Sat 25/10/2025 15:40 - v0.4.28 (stable) CRITICAL: Automatic fresh start when machine deleted from Supabase. CHE now detects 404 errors and triggers fresh start immediately without requiring service restart.

Sat 25/10/2025 15:11 - v0.4.27 (stable) CRITICAL FIX: PawnIO driver now properly unloaded on LHM shutdown to prevent lhm-cache file locks. Fresh start now excludes lhm-cache from deletion to preserve .NET runtime files. Fixes LHM service failing to start after fresh start.

Sat 25/10/2025 12:11 - v0.4.26 (stable) FIX: CHE cloud exporter now uses authenticated requests to ingest-rollup and ingest-signatures Edge Functions. This fixes 401 errors preventing inventory data from syncing to Supabase.

Sat 25/10/2025 11:50 - v0.4.25 (stable) CRITICAL FIX: Fresh start infinite loop when machine deleted from Supabase. Now skips check after fresh start to allow inventory sync.

Sat 25/10/2025 11:33 - v0.4.24 (stable) CRITICAL FIX: Scheduler thread now starts AFTER startup update check to prevent race condition blocking updates

Sat 25/10/2025 10:41 - v0.4.23 (stable) Self-contained LHM with embedded .NET runtime. No separate .NET installation needed.

Sat 25/10/2025 10:36 - v0.4.22 (stable) TEST: Version injection now enabled for self-contained LHM executable

Sat 25/10/2025 10:34 - v0.4.21 (stable) CRITICAL FIX: LHM service now built as self-contained with .NET runtime included. No separate .NET installation required.

Sat 25/10/2025 10:10 - v0.4.20 (stable) CRITICAL FIX: Exclude .NET executables from version injection to prevent LHM service corruption

Thu 23/10/2025 19:48 - v0.3.195 (stable) fixed ui display of performance computers

Thu 23/10/2025 19:33 - v0.3.194 (stable) proper detection of machine performance

Thu 23/10/2025 18:23 - v0.3.193 (stable) fixes with the updater and fixes on tagpulse exe

Thu 23/10/2025 18:07 - v0.3.192 (stable) FIX: TagPulse.exe now launches in user desktop session instead of Session 0. │

Thu 23/10/2025 17:53 - v0.3.191 (stable) REAL FIX: Updater now forces service restart if already running to ensure new binary loads. Fixes version sync showing old versions.

Thu 23/10/2025 17:40 - v0.3.190 (stable) FIX: Version sync race condition - service now always reads fresh from registry to avoid stale cache when service auto-starts before updater completes

Thu 23/10/2025 17:39 - v0.3.189 (stable) FIX: Version sync race condition - service now always reads fresh from registry to avoid stale cache when service auto-starts before updater completes

Thu 23/10/2025 16:58 - v0.3.188 (stable) check update of the supabase

Thu 23/10/2025 16:54 - v0.3.187 (stable) check update of the supabase

Thu 23/10/2025 16:29 - v0.3.186 (stable) fix sync issue tagpulseupdater with restarting service race

Thu 23/10/2025 16:23 - v0.3.185 (stable) fix sync issue tagpulseupdater with restarting service race

Thu 23/10/2025 16:01 - v0.3.184 (stable) FIX: Race condition causing version sync to report previous version. Registry now written BEFORE service restart.

Thu 23/10/2025 15:25 - v0.3.183 (stable) TEMP: Force inventory resync for 2 specific machines. Revert after sync.

Thu 23/10/2025 14:52 - v0.3.182 (stable) Critical CHE crash fix: null pointer protection │

Thu 23/10/2025 14:26 - v0.3.181 (stable) Critical fixes: performance caching crash prevention updater restart crash dump

Thu 23/10/2025 14:17 - v0.3.180Critical (stable) fixes: performance caching crash prevention updater restart crash dump

Thu 23/10/2025 14:10 - v0.3.179 (stable) fix sync version to db properly

Thu 23/10/2025 13:45 - v0.3.178 (stable) Critical fix: UpdateManager initialization + all timestamp fixes

Thu 23/10/2025 12:05 - v0.3.177 (stable) Fixed Supabase timestamp sync CHE dashboard hardware class fleet model fetching

Thu 23/10/2025 11:36 - v0.3.176 (stable) fixes timestamps to supabase

Thu 23/10/2025 11:20 - v0.3.175 (stable) fixes wrong recognition of mid-low-high pcs

Thu 23/10/2025 11:01 - v0.3.174 (stable) fixed bug with timestamps in supa

Thu 23/10/2025 08:50 - v0.3.173 (stable) lhm include net 8

Wed 22/10/2025 20:57 - v0.3.172 (stable) improved setup ui

Wed 22/10/2025 20:00 - v0.3.171 (stable) new setup build and fixes on the ui for low end pc

Wed 22/10/2025 19:33 - v0.3.170 (stable) che auto learning from cloud

Wed 22/10/2025 19:19 - v0.3.169 (stable) date time consisdience to all the supa

Wed 22/10/2025 18:40 - v0.3.168 (stable) different ui experience on low-mid-high perforamance pc

Wed 22/10/2025 18:14 - v0.3.167 (stable) different ui experience on low-mid-high perforamance pc

Wed 22/10/2025 15:19 - v0.3.165 (stable) timezone compatibility at supa

Wed 22/10/2025 14:04 - v0.3.164 (stable) ui tooltips

Wed 22/10/2025 13:21 - v0.3.163 (stable) CHE cloud learning v2

Tue 21/10/2025 17:08 - v0.3.162 (stable) fixed the updated at at supabase

Tue 21/10/2025 14:38 - v0.3.161 (stable) fixed the updated at at supabase

Tue 21/10/2025 14:27 - v0.3.160 (stable) new setup that allows exe files to av whitelist

Tue 21/10/2025 14:07 - v0.3.159 (stable) improve che accuracy addition of the version on pc at supa

Sun 19/10/2025 06:50 - v0.3.128 (stable) Test enhanced UI output

Sun 19/10/2025 06:50 - v0.3.127 (stable) Test enhanced UI

Sat 18/10/2025 21:02 - v0.3.126 (stable) adaptation bug fixed now correct baselines and manual update fix

Sat 18/10/2025 20:46 - v0.3.125 (stable) adaptation bug fixed now correct baselines

Sat 18/10/2025 19:59 - v0.3.124 (stable) fixes for the logs of che and after update start the tagpulse.exe

Sat 18/10/2025 19:19 - v0.3.123 (stable) fixes for the logs of che and after update start the tagpulse.exe

Sat 18/10/2025 18:31 - v0.3.122 (stable) CHE cloud priors logging - verification

Sat 18/10/2025 18:18 - v0.3.121 (stable) CHE cloud priors logging - verification

Sat 18/10/2025 18:08 - v0.3.120 (stable) log on che for confirmation on cloud support

Sat 18/10/2025 17:17 - v0.3.119 (stable) CHE cloud priors logging - verification

Sat 18/10/2025 17:06 - v0.3.119 (stable) Che confirmation of learning

Sat 18/10/2025 14:55 - v0.3.118 (stable) Auto-update crash recovery - check for updates before service init

Sat 18/10/2025 14:43 - v0.3.117 (stable) CHE alert fixes

Sat 18/10/2025 13:59 - v0.3.116 (stable) CHE alert threshold fixes

Sat 18/10/2025 13:57 - v0.3.116 (stable) fixing che critial problems

Sat 18/10/2025 12:53 - v0.3.115 (stable) Fix concurrent updates and add update notifications

Sat 18/10/2025 09:30 - v0.3.114 (stable) auto update fix

Sat 18/10/2025 09:17 - v0.3.113 (stable) polish ui updates and auto updates

Sat 18/10/2025 09:09 - v0.3.112 (stable) UI and auto-update fixes

Sat 18/10/2025 08:53 - v0.3.112 (stable) polish ui updates and auto updates

Sat 18/10/2025 08:38 - v0.3.111 (stable) Auto-update fix - Initialize UpdateManager in service startup

Sat 18/10/2025 08:12 - v0.3.110 (stable) UI progress display fix

Sat 18/10/2025 07:36 - v0.3.109 (stable) Auto-update diagnostics

Sat 18/10/2025 05:49 - v0.3.108 (stable) CPU fix for concurrent disk collections

Sat 18/10/2025 05:22 - v0.3.107 (stable) HTTP server CPU fix - reduced accept() polling from 10ms to 100ms (fixes constant 24% CPU on weak PCs)

Fri 17/10/2025 20:13 - v0.3.106 (stable) UI responsiveness fix

Fri 17/10/2025 19:59 - v0.3.105 (stable) Auto-update diagnostic logging

Fri 17/10/2025 19:43 - v0.3.104 (stable) Dashboard CPU fix

Fri 17/10/2025 19:37 - v0.3.103 (stable) Auto-update fix

Fri 17/10/2025 19:27 - v0.3.102 (stable) Dashboard CPU fix

Fri 17/10/2025 19:18 - v0.3.102 (stable) Dashboard CPU fix - respects hardware_poll_ms

Fri 17/10/2025 19:17 - v0.3.102 (stable) Dashboard CPU fix with rebuilt LHM binary

Fri 17/10/2025 19:06 - v0.3.101 (stable) dashboard CPU fix - respects hardware_poll_ms

Fri 17/10/2025 19:05 - v0.3.101 (stable) dashboard CPU fix - respects hardware_poll_ms

Fri 17/10/2025 19:05 - v0.3.101 (stable) dashboard CPU fix - respects hardware_poll_ms

Fri 17/10/2025 19:02 - v0.3.101+1760716430 (stable) dashboard CPU fix

Fri 17/10/2025 18:53 - v0.3.101 (stable) -ChangelogMessage Fix dashboard view hardcoded 2s interval - respects hardware_poll_ms config

Fri 17/10/2025 18:30 - v0.3.101 (stable) Fix dashboard view hardcoded 2s interval - respects hardware_poll_ms config

Fri 17/10/2025 18:19 - v0.3.100 (stable) Disable ETW network monitoring CPU killer

Fri 17/10/2025 18:10 - v0.3.99 (stable) Hardware polling 5s SMART is slow

Fri 17/10/2025 18:02 - v0.3.98 (stable) RefreshProcessList 30s svchost fix

Fri 17/10/2025 17:56 - v0.3.97 (stable) Process polling 5s the real fix

Fri 17/10/2025 17:21 - v0.3.96 (stable) Reduced process monitoring frequency 5s

Fri 17/10/2025 17:04 - v0.3.95 (stable) Network monitoring interval 10s fix

Fri 17/10/2025 16:57 - v0.3.94 (stable) Critical fix: sequential execution eliminates thread overhead

Fri 17/10/2025 16:48 - v0.3.93 (stable) Service CPU optimization: RefreshProcessList 5s + svchost cache

Fri 17/10/2025 16:37 - v0.3.92 (stable) reduce polling from 100ms to 1s

Fri 17/10/2025 14:09 - v0.3.91 (stable) Fixed SHA256 mismatch and performance optimizations

Fri 17/10/2025 14:07 - v0.3.90 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 14:00 - v0.3.89 (stable) Service CPU fix - reduced polling

Fri 17/10/2025 13:58 - v0.3.88 (stable) Service CPU fix - reduced polling from 100ms to 1s

Fri 17/10/2025 13:28 - v0.3.87 (stable) Changed performance icon to gauge speedometer for clarity

Fri 17/10/2025 13:19 - v0.3.86 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 13:10 - v0.3.85 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 13:03 - v0.3.84 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 12:51 - v0.3.83 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 12:31 - v0.3.82 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 12:30 - v0.3.81 (stable) improve reduce cpu usage and display usage

Fri 17/10/2025 12:11 - v0.3.80 (stable) sensors fix

Fri 17/10/2025 11:34 - v0.3.79 (stable) clean version repackage

Fri 17/10/2025 11:33 - v0.3.78 (stable) sensors fix and version cleanup

Fri 17/10/2025 11:29 - v0.3.77 (stable) sensors fix

Fri 17/10/2025 11:24 - v0.3.77 (stable) sensors fix

Sat 11/10/2025 09:24 - v0.3.76 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 08:51 - v0.3.75 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 08:50 - v0.3.74 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 08:26 - v0.3.73 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 08:20 - v0.3.72 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 07:55 - v0.3.71 (stable) fix ui not display pid and network top proccess usage

Sat 11/10/2025 07:17 - v0.3.70 (stable) fix json about che strings

Fri 10/10/2025 20:28 - v0.3.69 (stable) multi-pc test

Fri 10/10/2025 20:14 - v0.3.69 (stable) multi-pc test

Fri 10/10/2025 20:08 - v0.3.69 (stable) first try for multi update to many pcs

Fri 10/10/2025 19:57 - v0.3.69 (stable) first try for multi update to many pcs

Fri 10/10/2025 19:57 - v0.3.69 (stable) first try for multi update to many pcs

Fri 10/10/2025 19:31 - v0.3.68 (stable) first try for multi update to many pcs

Fri 10/10/2025 17:37 - v0.3.67 (stable) first try for multi update to many pcs

Fri 10/10/2025 10:46 - v0.3.66 (stable) republish all components

Fri 10/10/2025 10:45 - v0.3.67 (stable) update on cloud try 2

Fri 10/10/2025 10:27 - v0.3.66 (stable) update on cloud try 1

Fri 10/10/2025 10:07 - v0.3.65 (stable) update on cloud try 1

Fri 10/10/2025 09:53 - v0.3.64 (stable) cloud publish test

Fri 10/10/2025 09:30 - v0.3.63 (stable) update on cloud try 1

Thu 09/10/2025 13:10 - v0.3.62 (stable) fixed multi dumps on crash

Tue 07/10/2025 20:53 - v0.3.61 (stable) db connection verification

Tue 07/10/2025 16:10 - v0.3.60 (stable) che improvments with cloud control

Tue 07/10/2025 16:05 - v0.3.59 (stable) che improvments with cloud control

Tue 07/10/2025 15:40 - v0.3.58 (stable) che improvments with cloud control

Tue 07/10/2025 15:19 - v0.3.57 (stable) che improvments with cloud control

Tue 07/10/2025 14:21 - v0.3.56 (stable) update ui impovments

Tue 07/10/2025 14:10 - v0.3.55 (stable) cloud variables stay even after restart, cloud icon sucess or nor connected

Tue 07/10/2025 13:46 - v0.3.54 (stable) cloud variables stay even after restart, cloud icon sucess or nor connected

Tue 07/10/2025 13:40 - v0.3.53 (stable) cloud variables stay even after restart, cloud icon sucess or nor connected

Mon 06/10/2025 20:30 - v0.3.52 (stable) redusing the logs

Mon 06/10/2025 20:05 - v0.3.51 (stable) update ui fixes

Mon 06/10/2025 19:41 - v0.3.50 (stable) crash fix and on update try fix

Mon 06/10/2025 17:44 - v0.3.49 (stable) crash fix

Sun 05/10/2025 15:42 - v0.3.36 (stable) cloud improvemnts

Sun 05/10/2025 15:06 - v0.3.35 (stable) cloud improvemnts

Sun 05/10/2025 13:24 - v0.3.34 (stable) crash on exit try fix 45

Sun 05/10/2025 13:15 - v0.3.33 (stable) cloud insided stored

Sun 05/10/2025 12:48 - v0.3.32 (stable) ui version fixes and crash during shutdown

Sun 05/10/2025 12:43 - v0.3.31 (stable) ui version fixes

Sun 05/10/2025 12:37 - v0.3.30 (stable) che AV problem resolution

Sun 05/10/2025 11:56 - v0.3.29 (stable) che on cloud v1

Sun 05/10/2025 11:42 - v0.3.28 (stable) che on cloud v1

Sun 05/10/2025 11:15 - v0.3.27 (stable) che on cloud v1

Sun 05/10/2025 10:55 - v0.3.26 (stable) che on cloud v1

Sun 05/10/2025 10:45 - v0.3.25 (stable) che on cloud v1

Sun 05/10/2025 10:19 - v0.3.24 (stable) che on cloud v1

Sun 05/10/2025 10:05 - v0.3.23 (stable) che on cloud v1

Sun 05/10/2025 09:49 - v0.3.22 (stable) che on cloud v1

Sun 05/10/2025 09:32 - v0.3.21 (stable) che on cloud v1

Sat 04/10/2025 20:12 - v0.3.2 (stable) che on cloud v1

Sat 04/10/2025 18:48 - v0.3.1 (stable) che on cloud v1

Sat 04/10/2025 18:35 - v0.3.0 (stable) che on cloud v1

Sat 04/10/2025 17:49 - v0.3.0 (stable) che on cloud v1

Sat 04/10/2025 17:26 - v0.3.0 (stable) che on cloud v1

Fri 03/10/2025 17:58 - v0.2.5 (stable) che ui improvemtns

Fri 03/10/2025 17:22 - v0.2.4 (stable) network details fixes

Fri 03/10/2025 16:29 - v0.2.3 (stable) autoupdater and update poage ui improves

Fri 03/10/2025 13:53 - v0.2.1c (stable) autoupdater and update poage ui improves

Fri 03/10/2025 13:45 - v0.2.1b (stable) autoupdater and network details graph fixes

Fri 03/10/2025 13:09 - v0.2.1a (stable) autoupdater and network details graph fixes

Fri 03/10/2025 13:00 - v0.2.1 (stable) autoupdater and network details graph fixes

Fri 03/10/2025 13:00 - v0.2.0 (stable) autoupdater and network details graph fixes

Fri 03/10/2025 12:53 - v0.2.0 (stable) autoupdater and network details graph fixes

Fri 03/10/2025 12:21 - v0.2.0 (stable) autoupdater and network details graph fixes

Fri 03/10/2025 12:09 - v0.1.91 (stable) network details fixes

Fri 03/10/2025 11:42 - v0.1.90 (stable) update screen improvemnts

Thu 02/10/2025 15:17 - v0.1.9j (stable) update screen improvemnts

Thu 02/10/2025 15:04 - v0.1.9i (stable) che improvements

Thu 02/10/2025 14:42 - v0.1.9h (stable) che improvements

Thu 02/10/2025 14:10 - v0.1.9g (stable) che improvements

Thu 02/10/2025 13:27 - v0.1.9f (stable) che improvements

Thu 02/10/2025 13:04 - v0.1.9e (stable) che improvements

Thu 02/10/2025 12:25 - v0.1.9d (stable) che improvements

Thu 02/10/2025 12:18 - v0.1.9c (stable) che improvements

Thu 02/10/2025 12:03 - v0.1.9b (stable) che improvements

Thu 02/10/2025 11:31 - v0.1.9a (stable) che improvements

Wed 01/10/2025 21:13 - v0.1.9 (stable) che improvements

Wed 01/10/2025 15:47 - v0.1.8f (stable) fix motherboard sensors

Wed 01/10/2025 15:37 - v0.1.8e (stable) fix motherboard sensors

Wed 01/10/2025 14:27 - v0.1.8d (stable) fix motherboard sensors

Wed 01/10/2025 13:00 - v0.1.8c (stable) fix motherboard sensors

Wed 01/10/2025 12:51 - v0.1.8b (stable) fix motherboard sensors

Wed 01/10/2025 12:41 - v0.1.8a (stable) fix motherboard sensors

Wed 01/10/2025 12:32 - v0.1.8 (stable) fix motherboard sensors

Wed 01/10/2025 12:16 - v0.1.7ο (stable) fix motherboard sensors

Wed 01/10/2025 11:48 - v0.1.7n (stable) fix motherboard sensors

Wed 01/10/2025 11:38 - v0.1.7m (stable) fix motherboard sensors

Wed 01/10/2025 11:20 - v0.1.7L (stable) fix motherboard sensors

Tue 30/09/2025 20:34 - v0.1.7k (stable) fix motherboard sensors

Tue 30/09/2025 20:19 - v0.1.7j (stable) fix motherboard sensors

Tue 30/09/2025 20:05 - v0.1.7i (stable) fix motherboard sensors

Tue 30/09/2025 20:05 - v0.1.7i (stable) fix motherboard sensors

Tue 30/09/2025 19:56 - v0.1.7h (stable) fix motherboard sensors

Tue 30/09/2025 19:37 - v0.1.7g (stable) fix motherboard sensors

Tue 30/09/2025 19:05 - v0.1.7f (stable) fixing about and che slow load pagesv2

Tue 30/09/2025 18:35 - v0.1.7e (stable) fixing about and che slow load pages

Tue 30/09/2025 14:57 - v0.1.7d (stable) ui fixes

Tue 30/09/2025 14:45 - v0.1.7c (stable) crash fixes

Mon 29/09/2025 20:48 - v0.1.7b (stable) dashboard refinments

Mon 29/09/2025 18:16 - v0.1.7a (stable) dashboard refinments

Mon 29/09/2025 18:07 - v0.1.7 (stable) dashboard refinments

Mon 29/09/2025 17:47 - v0.1.6h (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 17:25 - v0.1.6g (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 17:20 - v0.1.6f (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 17:03 - v0.1.6e (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 16:49 - v0.1.6d (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 16:00 - v0.1.6c (stable) redesign the frontend backend communication sse mostly and updater fixes

Mon 29/09/2025 15:26 - v0.1.6b (stable) redesign the frontend backend communication sse mostly

Mon 29/09/2025 14:28 - v0.1.6a (stable) redesign the frontend backend communication

Mon 29/09/2025 14:17 - v0.1.6 (stable) redesign the frontend backend communication

Mon 29/09/2025 11:30 - v0.1.5q (stable) DB housekeeping: prune CHE/perf/software/session history; checkpoint WAL at startup; previous fixes included

Mon 29/09/2025 11:11 - v0.1.5p (stable) Startup housekeeping: keep only last 5 crash dumps; CPU speed display improved; previous fixes included

Sun 28/09/2025 20:46 - v0.1.5n (stable) CPU headline speed now uses peak core frequency; previous fixes included

Sun 28/09/2025 20:17 - v0.1.5m (stable) Updater: remove ProgramData\\TagPulse\\updates\\backup after success; DLLS JSON fixed; uiReload on any UI plan; ETW shutdown fix
Sun 05/10/2025 12:25 - v0.2.4 (stable) Updater: terminate TagPulse.exe before DESKTOP replace to avoid locked-file fallback; schedules replace-on-reboot only as last resort

Sun 28/09/2025 20:14 - v0.1.5l (stable) Fix /api/version DLLS JSON escaping; uiReload on any UI plan; ETW shutdown crash fix

Sun 28/09/2025 18:51 - v0.1.5k (stable) Force uiReload on any plan including UI; /api/version DLLS fallback; ETW shutdown crash fix present

Sun 28/09/2025 18:37 - v0.1.5j (stable) updater improvements and fixes v2 and crashes fixed

Sun 28/09/2025 18:32 - v0.1.5i (stable) Fix ETW shutdown crash (NetworkProcessMonitor stop), aggressive ProgramData cleanup, SMARTCTL label

Sun 28/09/2025 18:18 - v0.1.5h (stable) updater improvements and fixes v2

Sun 28/09/2025 17:40 - v0.1.5g (stable) updater improvements and fixes v2

Sun 28/09/2025 17:21 - v0.1.5f (stable) updater improvements and fixes

Sun 28/09/2025 17:07 - v0.1.5e (stable) updater improvements and fixes

Sun 28/09/2025 16:52 - v0.1.5c (stable) updater improvements and fixes

Sun 28/09/2025 16:36 - v0.1.5b (stable) updater fixes

Sun 28/09/2025 16:23 - v0.1.5a (stable) update fixes and che fixes

Sun 28/09/2025 16:11 - v0.1.5 (stable) update fixes and che fixes

Sun 28/09/2025 15:59 - v0.1.4g (stable) update fixes

Sun 28/09/2025 15:49 - v0.1.4f (stable) update fixes

Sun 28/09/2025 15:21 - v0.1.4e (stable) che fixes and ui cleance it is in place

Sun 28/09/2025 14:37 - v0.1.4d (stable) config page redesign

Sun 28/09/2025 14:20 - v0.1.4c (stable) config page redesign

Sun 28/09/2025 14:11 - v0.1.4b (stable) config page redesign

Sun 28/09/2025 13:42 - v0.1.4a (stable) update page redesign

Sun 28/09/2025 13:39 - v0.1.4 (stable) update page redesign

Sun 28/09/2025 12:55 - v0.1.3g (stable) motherboard fix and che fix

Sun 28/09/2025 12:13 - v0.1.3f (stable) motherboard problem

Sun 28/09/2025 11:58 - v0.1.3e (stable) gr fix and mothboard problem

Sun 28/09/2025 10:57 - v0.1.3d (stable) fixing che problem and motherboard not recognized

Sun 28/09/2025 10:48 - v0.1.3c (stable) fixing che problem and motherboard not recognized

Sun 28/09/2025 10:09 - v0.1.3b (stable) fixing #2 of the added date format to the config and to ui

Sun 28/09/2025 09:58 - v0.1.3a (stable) fixing of the added date format to the config and to ui

Sun 28/09/2025 09:49 - v0.1.3 (stable) added date format to the config and to ui

Sun 28/09/2025 09:35 - v0.1.2e (stable) automatic update of ui in case of update

Sun 28/09/2025 09:22 - v0.1.2d (stable) Config Page improvements

Sun 28/09/2025 08:48 - v0.1.2c (stable) UI Improvements and updater improvements


Sun 28/09/2025 07:35 - v0.1.2b (stable) UI Improvements

Sun 28/09/2025 07:23 - v0.1.2a (stable) UI Improvements

Sat 27/09/2025 20:03 - v0.1.2 (stable) Quicky test

Sat 27/09/2025 16:34 - v0.1.1 (stable) UI Improvements and bug fixes



Sat 27/09/2025 16:31 - v0.1.1 (stable) UI Improvements and bug fixes































































































































































































































































































