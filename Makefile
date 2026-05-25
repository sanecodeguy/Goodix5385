.PHONY: all install clean sigfm-python

all: sigfm

sigfm:
	$(MAKE) -C sigfm

sigfm-python:
	pip install -r requirements.txt

install: all
	# Install Python package
	pip install -e .
	# Install udev rule
	sudo cp udev/99-goodix-5385.rules /etc/udev/rules.d/
	sudo udevadm control --reload-rules
	# Install PAM module
	sudo cp pam/pam_goodix5385.py /usr/local/bin/
	sudo chmod +x /usr/local/bin/pam_goodix5385.py
	# Install sigfm binaries
	sudo cp sigfm/match.out /usr/local/bin/goodix5385-match
	sudo cp sigfm/compute.out /usr/local/bin/goodix5385-compute
	# Install scripts
	sudo cp scripts/capture.py /usr/local/bin/goodix5385-capture
	sudo cp scripts/enroll.py /usr/local/bin/goodix5385-enroll
	sudo cp scripts/authenticate.py /usr/local/bin/goodix5385-auth
	sudo chmod +x /usr/local/bin/goodix5385-*

clean:
	$(MAKE) -C sigfm clean
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
