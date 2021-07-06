# @summary Extends postgresql_base by tuning the configuration.
class zulip::profile::postgresql {
  include zulip::profile::base
  include zulip::postgresql_base

  $work_mem = $zulip::common::total_memory_mb / 512
  $shared_buffers = $zulip::common::total_memory_mb / 8
  $effective_cache_size = $zulip::common::total_memory_mb * 10 / 32
  $maintenance_work_mem = $zulip::common::total_memory_mb / 32

  $random_page_cost = zulipconf('postgresql', 'random_page_cost', undef)
  $effective_io_concurrency = zulipconf('postgresql', 'effective_io_concurrency', undef)
  $replication = zulipconf('postgresql', 'replication', undef)
  $listen_addresses = zulipconf('postgresql', 'listen_addresses', undef)

  $ssl_cert_file = zulipconf('postgresql', 'ssl_cert_file', undef)
  $ssl_key_file = zulipconf('postgresql', 'ssl_key_file', undef)
  $ssl_ca_file = zulipconf('postgresql', 'ssl_ca_file', undef)

  file { $zulip::postgresql_base::postgresql_confdirs:
    ensure => directory,
    owner  => 'postgres',
    group  => 'postgres',
  }

  $postgresql_conf_file = "${zulip::postgresql_base::postgresql_confdir}/postgresql.conf"
  file { $postgresql_conf_file:
    ensure  => file,
#    require => $zulip::postgresql_base::postgresql_user_reqs,
    owner   => 'postgres',
    group   => 'postgres',
    mode    => '0644',
    content => template("${zulip::postgresql_base::postgresql_template}"),
  }

  exec { $zulip::postgresql_base::postgresql_restart:
#    require     => $zulip::postgresql_base::postgresql_user_reqs,
    refreshonly => true,
    subscribe   => [ File[$postgresql_conf_file] ],
  }
}
