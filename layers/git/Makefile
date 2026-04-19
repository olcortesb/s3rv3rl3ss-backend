build-GitLayer:
	dnf install -y git
	mkdir -p "$(ARTIFACTS_DIR)/bin" "$(ARTIFACTS_DIR)/lib" "$(ARTIFACTS_DIR)/share/git-core"
	cp /usr/bin/git "$(ARTIFACTS_DIR)/bin/"
	cp /usr/libexec/git-core/git-remote-https "$(ARTIFACTS_DIR)/bin/"
	cp -r /usr/share/git-core/templates "$(ARTIFACTS_DIR)/share/git-core/"
	for bin in /usr/bin/git /usr/libexec/git-core/git-remote-https; do \
		for lib in $$(ldd "$$bin" | awk '/=>/ {print $$3}'); do \
			cp -n "$$lib" "$(ARTIFACTS_DIR)/lib/" 2>/dev/null || true; \
		done; \
	done
