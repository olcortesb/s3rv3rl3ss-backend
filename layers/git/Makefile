build-GitLayer:
	@if command -v dnf >/dev/null 2>&1; then \
		dnf install -y git; \
	fi
	mkdir -p "$(ARTIFACTS_DIR)/bin" "$(ARTIFACTS_DIR)/lib" "$(ARTIFACTS_DIR)/share/git-core"
	cp /usr/bin/git "$(ARTIFACTS_DIR)/bin/"
	cp /usr/libexec/git-core/git-remote-https "$(ARTIFACTS_DIR)/bin/" 2>/dev/null || \
		cp /usr/lib/git-core/git-remote-https "$(ARTIFACTS_DIR)/bin/"
	cp -r /usr/share/git-core/templates "$(ARTIFACTS_DIR)/share/git-core/"
	@# Copy only non-system libs (skip libc, libm, libpthread, libdl, librt, ld-linux)
	for bin in $(ARTIFACTS_DIR)/bin/git $(ARTIFACTS_DIR)/bin/git-remote-https; do \
		for lib in $$(ldd "$$bin" | awk '/=>/ {print $$3}'); do \
			case "$$lib" in \
				*/libc.so*|*/libm.so*|*/libpthread.so*|*/libdl.so*|*/librt.so*|*/ld-linux*|*/libresolv.so*) ;; \
				*) cp -n "$$lib" "$(ARTIFACTS_DIR)/lib/" 2>/dev/null || true ;; \
			esac; \
		done; \
	done
