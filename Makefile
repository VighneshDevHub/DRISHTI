PY ?= python
ifeq ($(OS),Windows_NT)
export PYTHONPATH := backend;backend/tests;.
else
export PYTHONPATH := backend:backend/tests:.
endif

.PHONY: install api dashboard test sim sim-attack sim-disguises sim-drift sim-enforce sim-mimicry clean

install:                 ## install backend + dashboard dependencies
	$(PY) -m pip install -r backend/requirements.txt
	cd dashboard && pnpm install --frozen-lockfile

api:                     ## run the API on :8000
	cd backend && PYTHONPATH=.:../ $(PY) -m uvicorn app.main:create_app --factory --reload --port 8000

dashboard:               ## run the Next.js dashboard on :3000
	cd dashboard && pnpm dev

test:                    ## run all backend tests (stdlib unittest; also pytest-compatible)
	$(PY) -m unittest discover -s backend/tests -v

sim:                     ## normal traffic against the running API
	$(PY) -m simulator.runner --base-url http://localhost:8000 --mode normal --delay 0.4

sim-attack:              ## S1: the PS attack end to end, no server needed
	$(PY) -m simulator.runner --inprocess --mode s1 --variant plain

sim-drift:               ## S4 slow drift: tight and over-broad contracts, with ablation
	$(PY) -m simulator.runner --inprocess --mode s4 --compare
	$(PY) -m simulator.runner --inprocess --mode s4 --compare --broad

sim-enforce:             ## Phase 6: S1 under enforcement (0 bytes leaked), then even if a human approves
	$(PY) -m simulator.runner --inprocess --mode s1 --enforce --history 20 --legit-after 10
	$(PY) -m simulator.runner --inprocess --mode s1 --enforce --approve --history 20 --legit-after 10

sim-mimicry:             ## S5: mimicry attacker is restricted, legitimate work continues
	$(PY) -m simulator.runner --inprocess --mode s5 --enforce

sim-disguises:           ## S1 across all 5 injection disguises
	$(PY) -m simulator.runner --inprocess --mode s1 --variant all --history 25

clean:
	rm -f backend/warden.db
