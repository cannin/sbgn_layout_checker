APPNAME := sbgn_layout_checker
CMD := ./cmd/sbgn_layout_checker
DIST := dist

.PHONY: all test release current clean

all: test release current

test:
	go test ./...

release: clean
	mkdir -p $(DIST)
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o $(DIST)/$(APPNAME)-linux-amd64 $(CMD)
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o $(DIST)/$(APPNAME)-linux-arm64 $(CMD)
	CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -o $(DIST)/$(APPNAME)-darwin-amd64 $(CMD)
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -o $(DIST)/$(APPNAME)-darwin-arm64 $(CMD)
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -o $(DIST)/$(APPNAME)-windows-amd64.exe $(CMD)
	CGO_ENABLED=0 GOOS=windows GOARCH=arm64 go build -o $(DIST)/$(APPNAME)-windows-arm64.exe $(CMD)

current:
	mkdir -p $(DIST)
	go build -o $(DIST)/$(APPNAME) $(CMD)

clean:
	rm -rf $(DIST)
