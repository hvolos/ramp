/*
 * Infiniswap, remote memory paging over RDMA
 * Copyright 2017 University of Michigan, Ann Arbor
 * GPLv2 License
 */

#include "rdma-common.h"

static int on_connect_request(struct rdma_cm_id *id);
static int on_connection(struct rdma_cm_id *id);
static int on_disconnect(struct rdma_cm_id *id);
static int on_event(struct rdma_cm_event *event);
static void usage(const char *argv0);

long page_size;
int running;
int fault_latency_us = 30; // default value

void usage(const char *prog_name) 
{
  fprintf(stderr, "usage: %s [-f latency] ip port\n", prog_name);
  exit(1);
}

int parse_args(int argc, char *argv[], char **ip, int *port, int *fault_latency_us) {
  int opt;
  
  *ip = NULL;
  *port = -1;

  while ((opt = getopt(argc, argv, "f:")) != -1) {
    switch (opt) {
      case 'f':
        *fault_latency_us = atoi(optarg);
        if (*fault_latency_us <= 0) {
            fprintf(stderr, "Error: Invalid fault latency value. It must be a positive integer.\n");
            return 1;
        }                
        break;
      default:
        usage(argv[0]);
        return 1;
    }
  }

  // Ensure the required arguments are provided
  if ((argc - optind) < 2) {
    usage(argv[0]);
    return 1;
  }

  // Get the IP address and port from the remaining arguments
  *ip = argv[optind];
  *port = atoi(argv[optind + 1]);

  if (*port <= 0 || *port > 65535) {
      fprintf(stderr, "Error: Invalid port number. It must be a positive integer between 1 and 65535.\n");
      return 1;
  }

  return 0;
}

int main(int argc, char **argv)
{
  struct sockaddr_in6 addr;
  struct rdma_cm_event *event = NULL;
  struct rdma_cm_id *listener = NULL;
  struct rdma_event_channel *ec = NULL;
  uint16_t port = 0;
  pthread_t free_mem_thread;

  char *ip_addr;
  int port_number;
  
  if (parse_args(argc, argv, &ip_addr, &port_number, &fault_latency_us) != 0) {
    usage(argv[0]);
    return 1;
  }

  page_size = sysconf(_SC_PAGE_SIZE);

  memset(&addr, 0, sizeof(addr));
  addr.sin6_family = AF_INET6;
  inet_pton(AF_INET6, ip_addr, &addr.sin6_addr);
  addr.sin6_port = htons(port_number);

  TEST_Z(ec = rdma_create_event_channel());
  TEST_NZ(rdma_create_id(ec, &listener, NULL, RDMA_PS_TCP));
  TEST_NZ(rdma_bind_addr(listener, (struct sockaddr *)&addr));
  TEST_NZ(rdma_listen(listener, 10)); /* backlog=10 is arbitrary */

  port = ntohs(rdma_get_src_port(listener));

  printf("listening on port %d.\n", port);

  //free
  running = 1;
  TEST_NZ(pthread_create(&free_mem_thread, NULL, (void *)free_mem, NULL));

  while (rdma_get_cm_event(ec, &event) == 0) {
    struct rdma_cm_event event_copy;

    memcpy(&event_copy, event, sizeof(*event));
    rdma_ack_cm_event(event);

    if (on_event(&event_copy))
      break;
  }

  rdma_destroy_id(listener);
  rdma_destroy_event_channel(ec);

  return 0;
}

int on_connect_request(struct rdma_cm_id *id)
{
  struct rdma_conn_param cm_params;

  printf("received connection request.\n");
  build_connection(id);
  build_params(&cm_params);
  TEST_NZ(rdma_accept(id, &cm_params));

  return 0;
}

int on_connection(struct rdma_cm_id *id)
{
  on_connect(id->context);

  printf("connection build\n");
  /* J: only server send mr, client doesn't */
  send_free_mem_size(id->context);

  return 0;
}

int on_disconnect(struct rdma_cm_id *id)
{
  printf("peer disconnected.\n");

  destroy_connection(id->context);
  return 0;
}

int on_event(struct rdma_cm_event *event)
{
  int r = 0;

  if (event->event == RDMA_CM_EVENT_CONNECT_REQUEST)
    r = on_connect_request(event->id);
  else if (event->event == RDMA_CM_EVENT_ESTABLISHED)
    r = on_connection(event->id);
  else if (event->event == RDMA_CM_EVENT_DISCONNECTED)
    r = on_disconnect(event->id);
  else
    die("on_event: unknown event.");

  return r;
}