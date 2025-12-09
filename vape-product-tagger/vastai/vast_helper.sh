#!/bin/bash
#
# Vast.ai Helper Script - Simplified Commands
# Provides easy file upload/download commands
#
# Usage:
#   ./vastai/vast_helper.sh upload <instance_id> <local_file> [remote_path]
#   ./vastai/vast_helper.sh download <instance_id> <remote_path> [local_path]
#   ./vastai/vast_helper.sh ssh <instance_id>
#   ./vastai/vast_helper.sh status <instance_id>
#   ./vastai/vast_helper.sh stop <instance_id>
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

COMMAND=$1
INSTANCE_ID=$2

if [ -z "$COMMAND" ] || [ -z "$INSTANCE_ID" ]; then
    echo "Usage: $0 <command> <instance_id> [args...]"
    echo ""
    echo "Commands:"
    echo "  upload <instance_id> <local_file> [remote_path]"
    echo "  download <instance_id> <remote_path> [local_path]"
    echo "  ssh <instance_id>"
    echo "  status <instance_id>"
    echo "  stop <instance_id>"
    echo ""
    echo "Examples:"
    echo "  $0 upload 12345 data/input/products.csv /workspace/data/"
    echo "  $0 download 12345 /workspace/output/ ./output/"
    echo "  $0 ssh 12345"
    exit 1
fi

case $COMMAND in
    upload)
        LOCAL_FILE=$3
        REMOTE_PATH=${4:-/workspace/data/}
        
        if [ -z "$LOCAL_FILE" ]; then
            echo -e "${RED}Error: Local file required${NC}"
            exit 1
        fi
        
        if [ ! -f "$LOCAL_FILE" ]; then
            echo -e "${RED}Error: File not found: $LOCAL_FILE${NC}"
            exit 1
        fi
        
        echo -e "${CYAN}Uploading $LOCAL_FILE to instance $INSTANCE_ID:$REMOTE_PATH${NC}"
        
        # Get SCP URL
        SCP_URL=$(vastai scp-url $INSTANCE_ID 2>&1)
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to get SCP URL${NC}"
            echo "$SCP_URL"
            exit 1
        fi
        
        # Parse SSH details (format: ssh://root@123.456.789.012:12345)
        SSH_HOST=$(echo "$SCP_URL" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        SSH_PORT=$(echo "$SCP_URL" | grep -oE ':[0-9]+$' | tr -d ':')
        
        echo -e "${CYAN}Copying file...${NC}"
        scp -P $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            "$LOCAL_FILE" root@${SSH_HOST}:${REMOTE_PATH}
        
        echo -e "${GREEN}✓ Upload complete${NC}"
        ;;
        
    download)
        REMOTE_PATH=$3
        LOCAL_PATH=${4:-.}
        
        if [ -z "$REMOTE_PATH" ]; then
            echo -e "${RED}Error: Remote path required${NC}"
            exit 1
        fi
        
        echo -e "${CYAN}Downloading $REMOTE_PATH from instance $INSTANCE_ID${NC}"
        
        # Get SCP URL
        SCP_URL=$(vastai scp-url $INSTANCE_ID 2>&1)
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to get SCP URL${NC}"
            echo "$SCP_URL"
            exit 1
        fi
        
        # Parse SSH details
        SSH_HOST=$(echo "$SCP_URL" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        SSH_PORT=$(echo "$SCP_URL" | grep -oE ':[0-9]+$' | tr -d ':')
        
        echo -e "${CYAN}Copying files...${NC}"
        scp -P $SSH_PORT -r -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            root@${SSH_HOST}:${REMOTE_PATH} "$LOCAL_PATH"
        
        echo -e "${GREEN}✓ Download complete${NC}"
        ;;
        
    ssh)
        echo -e "${CYAN}Connecting to instance $INSTANCE_ID...${NC}"
        vastai ssh $INSTANCE_ID
        ;;
        
    status)
        echo -e "${CYAN}Instance $INSTANCE_ID status:${NC}"
        echo ""
        vastai show instance $INSTANCE_ID
        ;;
        
    stop)
        echo -e "${YELLOW}Stopping instance $INSTANCE_ID...${NC}"
        vastai stop instance $INSTANCE_ID
        echo -e "${GREEN}✓ Instance stopped${NC}"
        ;;
        
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        exit 1
        ;;
esac
