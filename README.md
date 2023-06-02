# README - ansible_raft

This project, called ansible_raft, is a set of Ansible roles designed to transform a collection from upstream to downstream. This process is somewhat specific to Red Hat. In order to provide certify content over Ansible Automation Hub, collections are required to use the redhat namespace and, in the case of collections related to middleware products (like JBoss EAP or Red Hat SSO), it is also required to change name of the collection from the upstream version (Wildfly, Keycloak) to the downstream one (JBoss EAP, RH SSO).

ansible_raft takes care of the changes required, ensuring that the downstream collections is identical to the upstream, apart for the required naming changes.

## How to install the ansible_raft collection?

Like any other Ansible collection!

$ ansible-galaxy collection install middleware_automation.ansible_raft

## How to use ansible_raft?

Suppose you have an upstream collection called **isawesome** living in the namespace **mystuff**. So the fqdn of your collection is **mystuff.isawesome** (see what I did there?). Now, you want to generate a downstream version to deliver certified content to your customers. Your company is **thisisserious** and the downstream of your collection is now **stuff**, so the fqdn is **thisisserious.stuff** (yes, I'm sticking with it). The upstream collection is living in the **mystuff** organiation on github.com and the project is called **isawesome_collection**.

Here is an example playbook to use ansible_raft to generate the downstream collection (thisisserious.stuff) from the upstream one (mystuff.isawesome):

```
---
- import_playbook: ansible_raft.yml
  vars:
    upstream_name: isawesome
    upstream_namespace: mystuff
    downstream_name: stuff
    downstream_namespace: thisisserious
    post_processors_replacements:
     - match: "http://github.com/thisisserious/stuff"
       replace: "http://github.com/mystuff/isawesome"
```

Note the the post_processors_replacements variables allow ansible_raft user to specifiy strings that needs to be replace **after** the transformation process. As illustrated in the example above, the rewriting to content to match the downstream_namespace.downstream_collection_name can sometime transform content that needs to stay the same or replace differently.
