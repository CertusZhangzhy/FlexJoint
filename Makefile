SHELL=bash
SRC := $(shell pwd)
VERSION ?= 1.0
TGZ = build.tar.gz
SPEC = FlexJoint.spec
BUILD_PRODUCT_TGZ=$(SRC)/$(TGZ)

RPM_REVISION ?= build2
RPMBUILD=$(SRC)/rpmbuild

rpm:
	mkdir -p $(RPMBUILD)/{SPECS,RPMS,BUILDROOT}
	rm -f $(TGZ)
	tar cvzf $(TGZ) fabfile docs
	cp $(SPEC) $(RPMBUILD)/SPECS
	( \
        cd $(RPMBUILD); \
        rpmbuild -bb --define "_topdir $(RPMBUILD)" --define "version $(VERSION)" --define "revision $(RPM_REVISION)" --define "tarname $(BUILD_PRODUCT_TGZ)" SPECS/${SPEC}; \
        )
	rm -f $(TGZ)
